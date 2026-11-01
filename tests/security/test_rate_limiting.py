import httpx
import pytest

from eventcraft.config import AppSettings
from eventcraft.main import create_app


@pytest.mark.asyncio
async def test_rate_limiting_enforcement():
    settings = AppSettings(rate_limit_per_minute=5)
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First 5 should pass
        for _ in range(5):
            r = await client.get("/api/v1/health")
            assert r.status_code == 200

        # 6th should trigger 429 Rate Limit Exceeded
        r6 = await client.get("/api/v1/health")
        assert r6.status_code == 429
        assert r6.headers["content-type"] == "application/problem+json"
        assert r6.headers.get("retry-after") == "60"
        body = r6.json()
        assert body["status"] == 429
        assert "rate-limit-exceeded" in body["type"]


@pytest.mark.asyncio
async def test_body_size_limit_413():
    settings = AppSettings(body_limit_bytes=1024)
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)

    # 2 KB payload
    oversized_payload = {"padding": "x" * 2048}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/plans/generate", json=oversized_payload)
        assert r.status_code == 413
        assert r.headers["content-type"] == "application/problem+json"
        body = r.json()
        assert body["status"] == 413
        assert "payload-too-large" in body["type"]
