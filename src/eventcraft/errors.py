"""RFC 7807 problem details and exception handlers for EventCraft AI."""

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ProblemDetails(BaseModel):
    """RFC 7807 Problem Details representation."""

    type: str
    title: str
    status: int
    detail: str
    instance: str


class EventCraftError(Exception):
    """Base application exception."""

    def __init__(
        self, message: str, status_code: int = 500, error_type: str = "internal-error"
    ) -> None:
        """Initialize exception with message and HTTP status code."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type


class RateLimitExceededError(EventCraftError):
    """Raised when client exceeds rate limit quota."""

    def __init__(self, message: str = "Rate limit exceeded. Please retry later.") -> None:
        """Initialize 429 rate limit exception."""
        super().__init__(message, status_code=429, error_type="rate-limit-exceeded")


class PayloadTooLargeError(EventCraftError):
    """Raised when request body exceeds configured byte limit."""

    def __init__(self, message: str = "Request payload exceeds maximum allowed size.") -> None:
        """Initialize 413 payload too large exception."""
        super().__init__(message, status_code=413, error_type="payload-too-large")


def create_problem_response(
    status: int,
    title: str,
    detail: str,
    error_type: str,
    extra_headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Construct RFC 7807 compliant problem+json response."""
    resp_headers = dict(extra_headers or {})
    corr_id = resp_headers.get("x-correlation-id", str(uuid.uuid4()))
    problem = ProblemDetails(
        type=f"https://eventcraft.ai/errors/{error_type}",
        title=title,
        status=status,
        detail=detail,
        instance=f"urn:uuid:{corr_id}",
    )
    resp_headers["Content-Type"] = "application/problem+json"
    resp_headers["x-correlation-id"] = corr_id
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(),
        headers=resp_headers,
    )


HTTP_TOO_MANY_REQUESTS = 429


def register_error_handlers(app: FastAPI) -> None:
    """Register uniform RFC 7807 handlers across FastAPI application."""

    @app.exception_handler(EventCraftError)
    async def eventcraft_exception_handler(request: Request, exc: EventCraftError) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        headers: dict[str, str] = {}
        if exc.status_code == HTTP_TOO_MANY_REQUESTS:
            headers["Retry-After"] = "60"
        headers["x-correlation-id"] = corr_id
        return create_problem_response(
            status=exc.status_code,
            title="Application Error",
            detail=exc.message,
            error_type=exc.error_type,
            extra_headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        err_msg = "Invalid request parameters."
        if exc.errors():
            first = exc.errors()[0]
            loc = " -> ".join(str(p) for p in first.get("loc", []))
            err_msg = f"{loc}: {first.get('msg', 'validation failed')}"

        return create_problem_response(
            status=422,
            title="Validation Error",
            detail=err_msg,
            error_type="validation-error",
            extra_headers={"x-correlation-id": corr_id},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        return create_problem_response(
            status=exc.status_code,
            title="HTTP Error",
            detail=str(exc.detail),
            error_type="http-error",
            extra_headers={"x-correlation-id": corr_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        corr_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        return create_problem_response(
            status=500,
            title="Internal Server Error",
            detail="An unexpected error occurred while processing your request.",
            error_type="internal-server-error",
            extra_headers={"x-correlation-id": corr_id},
        )
