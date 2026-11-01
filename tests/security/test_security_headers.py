import httpx
import pytest

from eventcraft.config import AppSettings
from eventcraft.main import create_app


@pytest.fixture
def test_app():
    return create_app(AppSettings())


@pytest.mark.asyncio
async def test_security_headers_present_on_all_responses(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Check on 200 OK
        resp_200 = await client.get("/api/v1/health")
        assert "content-security-policy" in resp_200.headers
        assert "default-src 'self'" in resp_200.headers["content-security-policy"]
        assert resp_200.headers.get("x-content-type-options") == "nosniff"
        assert resp_200.headers.get("x-frame-options") == "DENY"
        assert resp_200.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in resp_200.headers.get("permissions-policy", "")
        assert "no-store" in resp_200.headers.get("cache-control", "")
        assert "x-correlation-id" in resp_200.headers

        # Check on 404 Not Found
        resp_404 = await client.get("/api/v1/nonexistent")
        assert "content-security-policy" in resp_404.headers
        assert resp_404.headers.get("x-content-type-options") == "nosniff"


@pytest.mark.asyncio
async def test_no_secret_keys_in_error_or_headers(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/plans/generate", content="invalid json")
        text_resp = resp.text
        assert "gemini" not in text_resp.lower()
        assert "api_key" not in text_resp.lower()
        assert "secret" not in text_resp.lower()
