"""FastAPI application factory with lifespan management and security middleware."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from eventcraft.api.router import api_router
from eventcraft.config import AppSettings
from eventcraft.domain.clock import SystemClock
from eventcraft.errors import register_error_handlers
from eventcraft.knowledge.loader import KnowledgeRepository
from eventcraft.llm.base import LLMClient
from eventcraft.llm.cache import SingleFlightCache
from eventcraft.llm.gemini import GeminiClient
from eventcraft.llm.offline import OfflineClient
from eventcraft.security.body_limit import BodySizeLimitMiddleware
from eventcraft.security.headers import SecurityHeadersMiddleware
from eventcraft.security.rate_limit import InMemoryRateLimiter, RateLimitMiddleware
from eventcraft.services.assistant import AssistantService
from eventcraft.services.planner import PlannerService

STATIC_DIR = Path(__file__).resolve().parent / "static"
EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"


def _setup_app_state(app: FastAPI, settings: AppSettings) -> None:
    """Initialize application domain services and resources."""
    knowledge = KnowledgeRepository.load_from_directory()
    cache = SingleFlightCache(
        ttl_seconds=settings.cache_ttl_seconds,
        max_size=settings.cache_max_size,
    )
    clock = SystemClock()
    semaphore = asyncio.Semaphore(settings.max_concurrent_llm_calls)

    api_key_val = settings.gemini_api_key.get_secret_value()
    llm: LLMClient
    if api_key_val and hasattr(app.state, "http_client"):
        llm = GeminiClient(
            api_key=settings.gemini_api_key,
            http_client=app.state.http_client,
            model=settings.gemini_model,
            timeout_seconds=settings.gemini_timeout_seconds,
        )
    else:
        llm = OfflineClient()

    app.state.knowledge_repo = knowledge
    app.state.planner_service = PlannerService(knowledge, llm, cache, clock, semaphore)
    app.state.assistant_service = AssistantService(knowledge, llm, clock, semaphore)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application resource lifecycles and HTTP client pools."""
    settings: AppSettings = getattr(app.state, "settings", AppSettings())
    http_client = httpx.AsyncClient(timeout=settings.gemini_timeout_seconds)
    app.state.http_client = http_client
    _setup_app_state(app, settings)

    try:
        yield
    finally:
        await http_client.aclose()


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Create and configure fully-hardened EventCraft AI application instance."""
    app_settings = settings or AppSettings()
    app = FastAPI(
        title="EventCraft AI",
        description=(
            "GenAI-powered planning assistant for weddings, birthdays, and community events."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    _setup_app_state(app, app_settings)

    # Register error handlers
    register_error_handlers(app)

    # 1. Body size limit middleware
    app.add_middleware(
        BodySizeLimitMiddleware,
        max_bytes=app_settings.body_limit_bytes,
    )

    # 2. Rate limit middleware
    rate_limiter = InMemoryRateLimiter(app_settings.rate_limit_per_minute)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=rate_limiter,
        trust_proxy=app_settings.trust_proxy,
    )

    # 3. Security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)

    # 4. GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 5. Strict CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Mount API routes
    app.include_router(api_router)

    # Mount examples if available
    if EXAMPLES_DIR.exists():
        app.mount("/examples", StaticFiles(directory=str(EXAMPLES_DIR)), name="examples")

    # Mount static frontend
    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
