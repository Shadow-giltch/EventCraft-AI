"""In-memory rate limiter with sliding window tracking per client IP."""

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from eventcraft.errors import create_problem_response


class InMemoryRateLimiter:
    """Sliding-window rate limiter tracking timestamps per client identifier."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        """Initialize limiter with quota per 60-second window."""
        self._quota = requests_per_minute
        self._history: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        """Evaluate if client IP is within rate quota for current rolling minute."""
        now = time.monotonic()
        cutoff = now - 60.0
        timestamps = self._history[client_ip]

        # Prune timestamps older than 60 seconds
        self._history[client_ip] = [ts for ts in timestamps if ts > cutoff]

        if len(self._history[client_ip]) >= self._quota:
            return False

        self._history[client_ip].append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce per-IP request quotas on API endpoints."""

    def __init__(
        self, app: object, limiter: InMemoryRateLimiter, trust_proxy: bool = False
    ) -> None:
        """Initialize rate limit middleware."""
        super().__init__(app)  # type: ignore[arg-type]
        self._limiter = limiter
        self._trust_proxy = trust_proxy

    def _extract_client_ip(self, request: Request) -> str:
        """Derive client IP respecting proxy trust configuration."""
        if self._trust_proxy:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "127.0.0.1"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Apply rate check only to /api/ routes."""
        if request.url.path.startswith("/api/"):
            client_ip = self._extract_client_ip(request)
            if not self._limiter.is_allowed(client_ip):
                return create_problem_response(
                    status=429,
                    title="Rate Limit Exceeded",
                    detail=(
                        "Too many requests. Please wait before submitting more planning requests."
                    ),
                    error_type="rate-limit-exceeded",
                    extra_headers={"Retry-After": "60"},
                )

        return await call_next(request)
