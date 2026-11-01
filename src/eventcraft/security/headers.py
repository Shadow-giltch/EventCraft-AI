"""Security headers and correlation tracking middleware."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "base-uri 'none'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce defense-in-depth HTTP security headers and correlation ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Inject correlation ID and secure response headers."""
        # Attach or propagate correlation id
        corr_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = corr_id

        response = await call_next(request)

        # Apply hardening headers
        response.headers["x-correlation-id"] = corr_id
        response.headers["content-security-policy"] = CSP_POLICY
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
        response.headers["permissions-policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["cross-origin-opener-policy"] = "same-origin"
        response.headers["cross-origin-resource-policy"] = "same-origin"

        # Apply Cache-Control: no-store on all API endpoints
        if request.url.path.startswith("/api/"):
            response.headers["cache-control"] = "no-store, no-cache, must-revalidate"

        # Apply HSTS if running over HTTPS
        if request.url.scheme == "https":
            response.headers["strict-transport-security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response
