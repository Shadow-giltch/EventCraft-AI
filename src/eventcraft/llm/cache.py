"""In-memory LRU and TTL response cache with single-flight deduplication."""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from eventcraft.llm.base import LLMResponse


@dataclass(frozen=True)
class CachedEntry:
    """Cached response metadata with absolute expiration timestamp."""

    response: LLMResponse
    expires_at: float


class SingleFlightCache:
    """Thread-safe and async-safe LRU cache with TTL and concurrent single-flight deduplication."""

    def __init__(self, ttl_seconds: float = 3600.0, max_size: int = 1000) -> None:
        """Initialize cache store with capacity and lifetime limits."""
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._entries: OrderedDict[str, CachedEntry] = OrderedDict()
        self._in_flight: dict[str, asyncio.Future[LLMResponse]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def compute_cache_key(
        canonical_brief: dict[str, Any],
        section: str,
        prompt_version: str,
        model: str,
    ) -> str:
        """Generate deterministic SHA-256 key from request attributes."""
        serialized_payload = json.dumps(canonical_brief, sort_keys=True)
        raw_key = f"{serialized_payload}|{section}|{prompt_version}|{model}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def get_or_compute(
        self,
        cache_key: str,
        compute_fn: Callable[[], Awaitable[LLMResponse]],
    ) -> tuple[LLMResponse, str]:
        """Fetch cached item or execute compute_fn with single-flight deduplication."""
        now = time.monotonic()
        async with self._lock:
            if cache_key in self._entries:
                entry = self._entries[cache_key]
                if entry.expires_at > now:
                    self._entries.move_to_end(cache_key)
                    return entry.response, "hit"
                del self._entries[cache_key]

            # Single-flight deduplication: check if another worker is computing
            if cache_key in self._in_flight:
                future = self._in_flight[cache_key]
                need_wait = True
            else:
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self._in_flight[cache_key] = future
                need_wait = False

        if need_wait:
            res = await future
            return res, "hit"

        # This worker executes the actual computation
        try:
            result = await compute_fn()
            async with self._lock:
                if len(self._entries) >= self._max_size:
                    self._entries.popitem(last=False)
                self._entries[cache_key] = CachedEntry(
                    response=result, expires_at=time.monotonic() + self._ttl_seconds
                )
                future.set_result(result)
            return result, "miss"
        except BaseException as exc:
            async with self._lock:
                if not future.done():
                    future.set_exception(exc)
            raise
        finally:
            async with self._lock:
                self._in_flight.pop(cache_key, None)
