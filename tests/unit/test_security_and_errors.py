"""Gap-closing tests for security middleware and RFC 7807 error handlers.

Uses a tiny FastAPI app with the SAME middleware stack order as eventcraft.main.create_app,
so these run without the knowledge base, settings or LLM wiring.
"""

import time
import uuid

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.requests import Request as StarletteRequest

from eventcraft.errors import (
    EventCraftError,
    PayloadTooLargeError,
    RateLimitExceededError,
    create_problem_response,
    register_error_handlers,
)
from eventcraft.security.body_limit import BodySizeLimitMiddleware
from eventcraft.security.headers import CSP_POLICY, SecurityHeadersMiddleware
from eventcraft.security.rate_limit import (
    InMemoryRateLimiter,
    RateLimitMiddleware,
)


class Item(BaseModel):
    n: int


def build_app(*, rpm=1000, max_bytes=1024, trust_proxy=False) -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_bytes)
    app.add_middleware(RateLimitMiddleware, limiter=InMemoryRateLimiter(rpm), trust_proxy=trust_proxy)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/v1/ping")
    async def ping():
        return {"ok": True}

    @app.post("/api/v1/echo")
    async def echo(request: Request):
        return {"len": len(await request.body())}

    @app.post("/api/v1/item")
    async def item(i: Item):
        return i

    @app.get("/plain")
    async def plain():
        return {"ok": True}

    @app.get("/api/v1/app-error")
    async def app_error(code: int = 418):
        raise EventCraftError("custom failure", status_code=code, error_type="teapot")

    @app.get("/api/v1/rate-error")
    async def rate_error():
        raise RateLimitExceededError()

    @app.get("/api/v1/big-error")
    async def big_error():
        raise PayloadTooLargeError()

    @app.get("/api/v1/http-error")
    async def http_error():
        raise HTTPException(status_code=404, detail="thing not found")

    @app.get("/api/v1/empty-validation")
    async def empty_validation():
        raise RequestValidationError([])

    @app.get("/api/v1/boom")
    async def boom():
        raise RuntimeError("secret internal detail /etc/passwd")

    return app


def client(app, base="http://test"):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url=base
    )


# =============================== security headers ==================================


@pytest.mark.asyncio
async def test_hardening_headers_present_on_api_and_static_paths():
    async with client(build_app()) as c:
        for path in ("/api/v1/ping", "/plain"):
            h = (await c.get(path)).headers
            assert h["content-security-policy"] == CSP_POLICY
            assert h["x-content-type-options"] == "nosniff"
            assert h["x-frame-options"] == "DENY"
            assert h["referrer-policy"] == "strict-origin-when-cross-origin"
            assert "camera=()" in h["permissions-policy"]
            assert h["cross-origin-opener-policy"] == "same-origin"
            assert h["cross-origin-resource-policy"] == "same-origin"


@pytest.mark.asyncio
async def test_cache_control_no_store_only_on_api_paths():
    async with client(build_app()) as c:
        assert "no-store" in (await c.get("/api/v1/ping")).headers["cache-control"]
        assert "no-store" not in (await c.get("/plain")).headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_hsts_only_over_https():
    app = build_app()
    async with client(app, "https://test") as c:
        assert "max-age=63072000" in (await c.get("/plain")).headers["strict-transport-security"]
    async with client(app, "http://test") as c:
        assert "strict-transport-security" not in (await c.get("/plain")).headers


@pytest.mark.asyncio
async def test_correlation_id_is_propagated_or_generated():
    async with client(build_app()) as c:
        r = await c.get("/plain", headers={"x-correlation-id": "trace-123"})
        assert r.headers["x-correlation-id"] == "trace-123"
        generated = (await c.get("/plain")).headers["x-correlation-id"]
        assert str(uuid.UUID(generated)) == generated


@pytest.mark.asyncio
async def test_error_responses_also_carry_security_headers():
    async with client(build_app(max_bytes=10)) as c:
        r = await c.post("/api/v1/echo", content=b"x" * 50)
    assert r.status_code == 413
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["content-security-policy"] == CSP_POLICY


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="KNOWN GAP: middleware-generated 413/429 bodies get a random `instance` UUID while the "
    "x-correlation-id header is overwritten with the request's id, so they disagree. "
    "Fix: pass request.state.correlation_id via extra_headers in rate_limit/body_limit.",
)
async def test_429_problem_instance_matches_correlation_header():
    async with client(build_app(rpm=1)) as c:
        await c.get("/api/v1/ping")
        r = await c.get("/api/v1/ping", headers={"x-correlation-id": "trace-abc"})
    assert r.status_code == 429
    assert r.headers["x-correlation-id"] == "trace-abc"
    assert r.json()["instance"] == "urn:uuid:trace-abc"


# =============================== body size limit ===================================


@pytest.mark.asyncio
async def test_body_exactly_at_limit_is_allowed_and_one_over_is_rejected():
    async with client(build_app(max_bytes=100)) as c:
        assert (await c.post("/api/v1/echo", content=b"x" * 100)).status_code == 200
        r = await c.post("/api/v1/echo", content=b"x" * 101)
    assert r.status_code == 413
    assert "100 bytes" in r.json()["detail"]
    assert r.headers["content-type"] == "application/problem+json"


@pytest.mark.asyncio
async def test_non_numeric_content_length_is_ignored_by_limiter():
    async with client(build_app(max_bytes=10)) as c:
        r = await c.post("/api/v1/echo", content=b"hi", headers={"content-length": "abc"})
    assert r.status_code != 413


@pytest.mark.asyncio
async def test_get_without_body_is_unaffected():
    async with client(build_app(max_bytes=1)) as c:
        assert (await c.get("/api/v1/ping")).status_code == 200


@pytest.mark.asyncio
@pytest.mark.xfail(
    strict=True,
    reason="KNOWN GAP (security): limit only inspects Content-Length, so a chunked upload with no "
    "Content-Length bypasses it. Fix: wrap `receive` and count bytes, or enforce at the proxy.",
)
async def test_chunked_upload_without_content_length_is_still_limited():
    async def chunks():
        for _ in range(8):
            yield b"x" * 256  # 2 KB total, limit 1 KB

    async with client(build_app(max_bytes=1024)) as c:
        r = await c.post("/api/v1/echo", content=chunks())
    assert r.status_code == 413


# =============================== rate limiter ======================================


def test_limiter_blocks_at_quota_and_recovers_after_window(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    lim = InMemoryRateLimiter(2)
    assert lim.is_allowed("ip") and lim.is_allowed("ip")
    assert lim.is_allowed("ip") is False
    now[0] += 59.9
    assert lim.is_allowed("ip") is False
    now[0] += 0.2  # 60.1s after the first hits
    assert lim.is_allowed("ip") is True


def test_limiter_window_boundary_is_exclusive(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    lim = InMemoryRateLimiter(1)
    assert lim.is_allowed("ip")
    now[0] = 60.0  # exactly 60s later: old stamp is pruned
    assert lim.is_allowed("ip")


def test_limiter_tracks_clients_independently():
    lim = InMemoryRateLimiter(1)
    assert lim.is_allowed("a") and lim.is_allowed("b")
    assert not lim.is_allowed("a") and not lim.is_allowed("b")


def test_denied_requests_do_not_extend_the_window(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    lim = InMemoryRateLimiter(1)
    assert lim.is_allowed("ip")
    for t in (10, 20, 30, 40, 50):
        now[0] = t
        assert not lim.is_allowed("ip")
    now[0] = 61.0
    assert lim.is_allowed("ip")


@pytest.mark.asyncio
async def test_middleware_limits_only_api_paths():
    async with client(build_app(rpm=1)) as c:
        assert (await c.get("/api/v1/ping")).status_code == 200
        r = await c.get("/api/v1/ping")
        assert r.status_code == 429
        assert r.headers["retry-after"] == "60"
        assert r.json()["type"].endswith("/rate-limit-exceeded")
        for _ in range(5):
            assert (await c.get("/plain")).status_code == 200


@pytest.mark.asyncio
async def test_forwarded_for_ignored_unless_proxy_trusted():
    app = build_app(rpm=1, trust_proxy=False)
    async with client(app) as c:
        assert (await c.get("/api/v1/ping", headers={"x-forwarded-for": "1.1.1.1"})).status_code == 200
        # spoofing a different XFF must NOT grant a fresh bucket
        assert (await c.get("/api/v1/ping", headers={"x-forwarded-for": "2.2.2.2"})).status_code == 429


@pytest.mark.asyncio
async def test_forwarded_for_first_hop_used_when_proxy_trusted():
    app = build_app(rpm=1, trust_proxy=True)
    async with client(app) as c:
        h = lambda ip: {"x-forwarded-for": ip}  # noqa: E731
        assert (await c.get("/api/v1/ping", headers=h("1.1.1.1, 9.9.9.9"))).status_code == 200
        assert (await c.get("/api/v1/ping", headers=h("1.1.1.1, 8.8.8.8"))).status_code == 429
        assert (await c.get("/api/v1/ping", headers=h("2.2.2.2"))).status_code == 200
        # trusted proxy but header missing -> falls back to socket peer
        assert (await c.get("/api/v1/ping")).status_code == 200


def test_extract_client_ip_defaults_when_no_client():
    mw = RateLimitMiddleware(app=lambda *a: None, limiter=InMemoryRateLimiter(1))
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "client": None}
    assert mw._extract_client_ip(StarletteRequest(scope)) == "127.0.0.1"


# =============================== error handlers ====================================


@pytest.mark.asyncio
async def test_eventcraft_error_maps_status_type_and_detail():
    async with client(build_app()) as c:
        r = await c.get("/api/v1/app-error?code=418")
    body = r.json()
    assert r.status_code == 418
    assert r.headers["content-type"] == "application/problem+json"
    assert body["type"] == "https://eventcraft.ai/errors/teapot"
    assert body["detail"] == "custom failure"
    assert body["status"] == 418
    assert "retry-after" not in r.headers


@pytest.mark.asyncio
async def test_429_application_error_gets_retry_after():
    async with client(build_app()) as c:
        r = await c.get("/api/v1/rate-error")
    assert r.status_code == 429
    assert r.headers["retry-after"] == "60"
    assert r.json()["type"].endswith("/rate-limit-exceeded")


@pytest.mark.asyncio
async def test_payload_too_large_subclass_defaults():
    async with client(build_app()) as c:
        r = await c.get("/api/v1/big-error")
    assert r.status_code == 413
    assert r.json()["type"].endswith("/payload-too-large")


@pytest.mark.asyncio
async def test_http_exception_is_rendered_as_problem_json():
    async with client(build_app()) as c:
        r = await c.get("/api/v1/http-error")
    assert r.status_code == 404
    assert r.json()["detail"] == "thing not found"
    assert r.json()["type"].endswith("/http-error")


@pytest.mark.asyncio
async def test_unknown_route_is_problem_json_404():
    async with client(build_app()) as c:
        r = await c.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"


@pytest.mark.asyncio
async def test_validation_error_detail_names_the_field_path():
    async with client(build_app()) as c:
        r = await c.post("/api/v1/item", json={"n": "not-an-int"})
    assert r.status_code == 422
    assert r.json()["detail"].startswith("body -> n:")
    assert r.json()["type"].endswith("/validation-error")


@pytest.mark.asyncio
async def test_validation_error_with_no_errors_uses_generic_message():
    async with client(build_app()) as c:
        r = await c.get("/api/v1/empty-validation")
    assert r.status_code == 422
    assert r.json()["detail"] == "Invalid request parameters."


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500_without_leaking_internals():
    async with client(build_app()) as c:
        r = await c.get("/api/v1/boom")
    assert r.status_code == 500
    assert r.headers["content-type"] == "application/problem+json"
    assert "secret" not in r.text and "passwd" not in r.text
    assert r.json()["type"].endswith("/internal-server-error")


def test_create_problem_response_uses_supplied_or_generated_correlation_id():
    given = create_problem_response(400, "t", "d", "x", {"x-correlation-id": "abc"})
    assert given.headers["x-correlation-id"] == "abc"
    assert b"urn:uuid:abc" in given.body

    generated = create_problem_response(400, "t", "d", "x")
    uuid.UUID(generated.headers["x-correlation-id"])  # valid uuid, no exception


def test_create_problem_response_does_not_mutate_callers_headers():
    extra = {"Retry-After": "60"}
    create_problem_response(429, "t", "d", "x", extra)
    assert extra == {"Retry-After": "60"}
