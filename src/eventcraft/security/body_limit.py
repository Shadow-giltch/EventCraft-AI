"""Request body size limit middleware protecting against payload inflation."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from eventcraft.errors import create_problem_response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies exceeding configured maximum size."""

    def __init__(self, app: object, max_bytes: int = 32768) -> None:
        """Initialize middleware with maximum body limit in bytes."""
        super().__init__(app)  # type: ignore[arg-type]
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Intercept and check Content-Length before passing request downstream."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self._max_bytes:
                    return create_problem_response(
                        status=413,
                        title="Payload Too Large",
                        detail=(
                            "Request size exceeds maximum allowed limit of "
                            f"{self._max_bytes} bytes."
                        ),
                        error_type="payload-too-large",
                    )
            except ValueError:
                pass

        return await call_next(request)
