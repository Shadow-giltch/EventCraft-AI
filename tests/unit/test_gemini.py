"""Gap-closing tests for eventcraft.llm.gemini.GeminiClient (no real network)."""

import json

import httpx
import pytest
from pydantic import SecretStr

from eventcraft.llm import gemini as gemini_mod
from eventcraft.llm.gemini import RETRY_STATUS_CODES, GeminiClient, LLMProviderError

FAKE_KEY = "unit-test-key-not-real"


def ok_body(text="{}", tokens=7):
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
        "usageMetadata": {"totalTokenCount": tokens},
    }


class Harness:
    """Scripted transport: each entry is an httpx.Response or an Exception to raise."""

    def __init__(self, script):
        self.script, self.requests, self.sleeps = list(script), [], []

    def handler(self, request):
        self.requests.append(request)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def fake_sleep(self, seconds):
        self.sleeps.append(seconds)

    def client(self, monkeypatch, **kw):
        monkeypatch.setattr(gemini_mod.asyncio, "sleep", self.fake_sleep)
        http = httpx.AsyncClient(transport=httpx.MockTransport(self.handler))
        return GeminiClient(api_key=SecretStr(FAKE_KEY), http_client=http, **kw)


def R(status, body=None):
    return httpx.Response(status, json=body if body is not None else {})


# ---- happy path / request shape -------------------------------------------------


@pytest.mark.asyncio
async def test_success_parses_text_tokens_and_min_latency(monkeypatch):
    h = Harness([R(200, ok_body("hello", 42))])
    out = await h.client(monkeypatch).generate("prompt")
    assert (out.content, out.source, out.tokens_used) == ("hello", "ai", 42)
    assert out.latency_ms >= 1


@pytest.mark.asyncio
async def test_key_goes_in_header_never_in_url_or_body(monkeypatch):
    h = Harness([R(200, ok_body())])
    await h.client(monkeypatch, model="my-model").generate("p", temperature=0.9, max_output_tokens=77)
    req = h.requests[0]
    assert req.headers["x-goog-api-key"] == FAKE_KEY
    assert FAKE_KEY not in str(req.url)
    assert FAKE_KEY not in req.content.decode()
    assert str(req.url).endswith("/my-model:generateContent")
    body = json.loads(req.content)
    assert body["generationConfig"] == {
        "responseMimeType": "application/json",
        "temperature": 0.9,
        "maxOutputTokens": 77,
    }
    assert body["contents"][0]["parts"][0]["text"] == "p"


# ---- retry behaviour ------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("status", RETRY_STATUS_CODES)
async def test_retryable_status_then_success(monkeypatch, status):
    h = Harness([R(status), R(200, ok_body("recovered"))])
    out = await h.client(monkeypatch).generate("p")
    assert out.content == "recovered"
    assert len(h.requests) == 2
    assert len(h.sleeps) == 1


@pytest.mark.asyncio
async def test_retries_exhausted_raises_with_status_and_no_key_leak(monkeypatch):
    h = Harness([R(503), R(503), R(503)])
    with pytest.raises(LLMProviderError, match="503") as ei:
        await h.client(monkeypatch, max_retries=2).generate("p")
    assert FAKE_KEY not in str(ei.value)
    assert len(h.requests) == 3
    assert len(h.sleeps) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404])
async def test_non_retryable_status_fails_fast(monkeypatch, status):
    h = Harness([R(status)])
    with pytest.raises(LLMProviderError, match=str(status)):
        await h.client(monkeypatch).generate("p")
    assert len(h.requests) == 1
    assert h.sleeps == []


@pytest.mark.asyncio
async def test_backoff_is_exponential_with_bounded_jitter(monkeypatch):
    h = Harness([R(500), R(500), R(200, ok_body())])
    await h.client(monkeypatch, max_retries=2).generate("p")
    assert 1.1 <= h.sleeps[0] <= 1.5
    assert 2.1 <= h.sleeps[1] <= 2.5


@pytest.mark.asyncio
async def test_zero_retries_means_single_attempt(monkeypatch):
    h = Harness([R(503)])
    with pytest.raises(LLMProviderError):
        await h.client(monkeypatch, max_retries=0).generate("p")
    assert len(h.requests) == 1 and h.sleeps == []


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [httpx.ReadTimeout("t"), httpx.ConnectError("c")])
async def test_timeout_or_network_error_is_retried(monkeypatch, exc):
    h = Harness([exc, R(200, ok_body("ok"))])
    assert (await h.client(monkeypatch).generate("p")).content == "ok"
    assert len(h.sleeps) == 1


@pytest.mark.asyncio
async def test_persistent_network_error_wraps_and_chains_cause(monkeypatch):
    err = httpx.ConnectTimeout("slow")
    h = Harness([err, err, err])
    with pytest.raises(LLMProviderError, match="connection error") as ei:
        await h.client(monkeypatch, max_retries=2).generate("p")
    assert ei.value.__cause__ is err


# ---- response shape edge cases --------------------------------------------------


@pytest.mark.asyncio
async def test_no_candidates_raises(monkeypatch):
    for body in ({}, {"candidates": []}):
        h = Harness([R(200, body)])
        with pytest.raises(LLMProviderError, match="no candidate"):
            await h.client(monkeypatch).generate("p")


@pytest.mark.asyncio
async def test_missing_usage_metadata_gives_none_tokens(monkeypatch):
    h = Harness([R(200, {"candidates": [{"content": {"parts": [{"text": "t"}]}}]})])
    assert (await h.client(monkeypatch).generate("p")).tokens_used is None


@pytest.mark.asyncio
async def test_candidate_without_content_returns_empty_text(monkeypatch):
    h = Harness([R(200, {"candidates": [{"finishReason": "SAFETY"}]})])
    assert (await h.client(monkeypatch).generate("p")).content == ""


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    raises=IndexError,
    reason="KNOWN GAP: `parts: []` raises IndexError instead of LLMProviderError/empty text. "
    "Fix: `parts = content.get('parts') or [{}]` in GeminiClient.generate.",
)
async def test_candidate_with_empty_parts_list_is_handled_gracefully(monkeypatch):
    h = Harness([R(200, {"candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}]})])
    try:
        out = await h.client(monkeypatch).generate("p")
        assert out.content == ""
    except LLMProviderError:
        pass  # also acceptable
