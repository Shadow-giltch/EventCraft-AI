"""Gap-closing tests for eventcraft.llm.cache.SingleFlightCache."""

import asyncio

import pytest

from eventcraft.llm.base import LLMResponse
from eventcraft.llm.cache import SingleFlightCache


def resp(text="x"):
    return LLMResponse(content=text, source="ai", latency_ms=1, tokens_used=None)


class Counter:
    def __init__(self, text="x", delay=0.0, exc=None):
        self.calls = 0
        self.text, self.delay, self.exc = text, delay, exc

    async def __call__(self):
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc
        return resp(self.text)


# ---- key derivation -------------------------------------------------------------


def test_cache_key_is_deterministic_and_order_independent():
    k = SingleFlightCache.compute_cache_key
    assert k({"a": 1, "b": 2}, "s", "v1", "m") == k({"b": 2, "a": 1}, "s", "v1", "m")
    assert len(k({}, "s", "v1", "m")) == 64


@pytest.mark.parametrize("field", ["brief", "section", "version", "model"])
def test_cache_key_changes_when_any_component_changes(field):
    k = SingleFlightCache.compute_cache_key
    base = dict(brief={"a": 1}, section="s", version="v1", model="m")
    changed = dict(base, **{field: {"a": 2} if field == "brief" else "other"})
    assert k(base["brief"], base["section"], base["version"], base["model"]) != k(
        changed["brief"], changed["section"], changed["version"], changed["model"]
    )


# ---- hit / miss / ttl / lru -----------------------------------------------------


@pytest.mark.asyncio
async def test_miss_then_hit_calls_compute_once():
    cache, fn = SingleFlightCache(), Counter("one")
    r1, s1 = await cache.get_or_compute("k", fn)
    r2, s2 = await cache.get_or_compute("k", fn)
    assert (s1, s2) == ("miss", "hit")
    assert r1 is r2
    assert fn.calls == 1


@pytest.mark.asyncio
async def test_expired_entry_is_recomputed():
    cache, fn = SingleFlightCache(ttl_seconds=0.0), Counter()
    assert (await cache.get_or_compute("k", fn))[1] == "miss"
    assert (await cache.get_or_compute("k", fn))[1] == "miss"
    assert fn.calls == 2


@pytest.mark.asyncio
async def test_lru_evicts_least_recently_used_not_oldest_inserted():
    cache = SingleFlightCache(max_size=2)
    fa, fb, fc = Counter("a"), Counter("b"), Counter("c")
    await cache.get_or_compute("a", fa)
    await cache.get_or_compute("b", fb)
    assert (await cache.get_or_compute("a", fa))[1] == "hit"  # a is now most recent
    await cache.get_or_compute("c", fc)  # evicts b
    assert (await cache.get_or_compute("a", fa))[1] == "hit"
    assert (await cache.get_or_compute("b", fb))[1] == "miss"
    assert fb.calls == 2


@pytest.mark.asyncio
async def test_distinct_keys_do_not_share_results():
    cache = SingleFlightCache()
    a, _ = await cache.get_or_compute("a", Counter("A"))
    b, _ = await cache.get_or_compute("b", Counter("B"))
    assert (a.content, b.content) == ("A", "B")


# ---- single flight --------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_identical_requests_share_one_computation():
    cache, fn = SingleFlightCache(), Counter("shared", delay=0.05)
    results = await asyncio.gather(*(cache.get_or_compute("k", fn) for _ in range(6)))
    assert fn.calls == 1
    assert sorted(s for _, s in results) == ["hit"] * 5 + ["miss"]
    assert len({id(r) for r, _ in results}) == 1


@pytest.mark.asyncio
async def test_concurrent_different_keys_compute_independently():
    cache, fn = SingleFlightCache(), Counter(delay=0.02)
    await asyncio.gather(cache.get_or_compute("a", fn), cache.get_or_compute("b", fn))
    assert fn.calls == 2


# ---- failure behaviour ----------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_failure_propagates_is_not_cached_and_allows_retry():
    cache = SingleFlightCache()
    with pytest.raises(ValueError, match="boom"):
        await cache.get_or_compute("k", Counter(exc=ValueError("boom")))
    assert cache._in_flight == {}
    ok = Counter("recovered")
    r, status = await cache.get_or_compute("k", ok)
    assert (r.content, status) == ("recovered", "miss")


@pytest.mark.asyncio
async def test_waiters_receive_the_leaders_exception():
    cache = SingleFlightCache()
    fn = Counter(delay=0.05, exc=ValueError("boom"))
    results = await asyncio.gather(
        *(cache.get_or_compute("k", fn) for _ in range(4)), return_exceptions=True
    )
    assert fn.calls == 1
    assert all(isinstance(r, ValueError) for r in results)
    assert cache._in_flight == {}
