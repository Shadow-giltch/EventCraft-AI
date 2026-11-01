"""Google Gemini REST API client adhering to strict header authentication and retries."""

import asyncio
import secrets
import time
from typing import Any

import httpx
from pydantic import SecretStr

from eventcraft.llm.base import LLMResponse

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
HTTP_OK = 200
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)


class LLMProviderError(Exception):
    """Raised when upstream LLM provider fails after retries."""


class GeminiClient:
    """REST client calling Google Gemini with header authentication and jittered backoff."""

    def __init__(
        self,
        api_key: SecretStr,
        http_client: httpx.AsyncClient,
        model: str = "gemini-3.5-flash-lite",
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
    ) -> None:
        """Initialize Gemini client with secret key and shared HTTP transport."""
        self._api_key = api_key
        self._http = http_client
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._rng = secrets.SystemRandom()

    async def _post_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute POST request with exponential backoff on 429, 5xx, or network timeouts."""
        url = f"{BASE_URL}/{self._model}:generateContent"
        headers = {
            "x-goog-api-key": self._api_key.get_secret_value(),
            "Content-Type": "application/json",
        }

        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
                if resp.status_code == HTTP_OK:
                    data: dict[str, Any] = resp.json()
                    return data
                if resp.status_code in RETRY_STATUS_CODES and attempt < self._max_retries:
                    backoff = (2**attempt) + self._rng.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff)
                    continue
                raise LLMProviderError(f"Gemini call failed with status code {resp.status_code}")
            except (httpx.TimeoutException, httpx.NetworkError) as err:
                if attempt < self._max_retries:
                    backoff = (2**attempt) + self._rng.uniform(0.1, 0.5)
                    await asyncio.sleep(backoff)
                    continue
                raise LLMProviderError(f"Gemini connection error: {err}") from err

        raise LLMProviderError("Max retries exceeded while calling Gemini API")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
    ) -> LLMResponse:
        """Call Gemini REST API requesting JSON response."""
        start_time = time.monotonic()
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }

        raw_data = await self._post_with_retry(payload)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        candidates = raw_data.get("candidates", [])
        if not candidates:
            raise LLMProviderError("Gemini response contained no candidate completions")

        first_part = candidates[0].get("content", {}).get("parts", [{}])[0]
        text_content = first_part.get("text", "")

        usage = raw_data.get("usageMetadata", {})
        total_tokens = usage.get("totalTokenCount")

        return LLMResponse(
            content=text_content,
            source="ai",
            latency_ms=max(1, elapsed_ms),
            tokens_used=total_tokens,
        )
