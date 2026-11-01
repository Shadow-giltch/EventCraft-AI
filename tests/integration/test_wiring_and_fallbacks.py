"""Wiring + degraded-mode tests for main.py, PlannerService and AssistantService.

NOTE: written against your real modules (config, api.router, knowledge, offline, schemas).
They could not be executed outside your repo, so run them first and tell me about any failure.
Assumption: routers read services from `request.app.state` at request time.
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr

from eventcraft.config import AppSettings
from eventcraft.domain.clock import SystemClock
from eventcraft.llm.base import LLMResponse
from eventcraft.llm.cache import SingleFlightCache
from eventcraft.llm.gemini import GeminiClient
from eventcraft.llm.offline import OfflineClient
from eventcraft.llm.prompts import OFF_TOPIC_REFUSAL
from eventcraft.main import create_app
from eventcraft.services.assistant import AssistantService
from eventcraft.services.planner import PlannerService


class FailingLLM:
    async def generate(self, prompt, temperature=0.2, max_output_tokens=1024):
        raise RuntimeError("upstream down")


class ScriptedLLM:
    def __init__(self, content):
        self.content, self.calls = content, 0

    async def generate(self, prompt, temperature=0.2, max_output_tokens=1024):
        self.calls += 1
        return LLMResponse(content=self.content, source="ai", latency_ms=1, tokens_used=1)


def http(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def brief(days=120):
    return {
        "event_type": "wedding",
        "event_date": (date.today() + timedelta(days=days)).isoformat(),
        "guest_count": 100,
        "budget_total": "20000.00",
        "currency": "USD",
    }


def swap_assistant(app, llm):
    app.state.assistant_service = AssistantService(
        app.state.knowledge_repo, llm, SystemClock(), asyncio.Semaphore(2)
    )


def swap_planner(app, llm):
    app.state.planner_service = PlannerService(
        app.state.knowledge_repo, llm, SingleFlightCache(), SystemClock(), asyncio.Semaphore(2)
    )


# ------------------------------- main.py wiring ---------------------------------


@pytest.mark.asyncio
async def test_lifespan_uses_gemini_when_key_present_and_closes_http_client():
    app = create_app(AppSettings(gemini_api_key=SecretStr("unit-test-key-not-real")))
    async with app.router.lifespan_context(app):
        assert isinstance(app.state.assistant_service._llm, GeminiClient)
        assert not app.state.http_client.is_closed
    assert app.state.http_client.is_closed


@pytest.mark.asyncio
async def test_lifespan_falls_back_to_offline_client_without_key():
    app = create_app(AppSettings(gemini_api_key=SecretStr("")))
    async with app.router.lifespan_context(app):
        assert isinstance(app.state.assistant_service._llm, OfflineClient)


@pytest.mark.asyncio
async def test_cors_allows_default_origin_only():
    app = create_app(AppSettings())
    pre = {"Access-Control-Request-Method": "POST"}
    async with http(app) as c:
        good = await c.options("/api/v1/health", headers={"Origin": "http://localhost:3000", **pre})
        bad = await c.options("/api/v1/health", headers={"Origin": "https://evil.example", **pre})
    assert good.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in bad.headers


@pytest.mark.asyncio
async def test_rate_limited_response_still_has_cors_and_security_headers():
    app = create_app(AppSettings(rate_limit_per_minute=5))
    h = {"Origin": "http://localhost:3000"}
    async with http(app) as c:
        for _ in range(5):
            await c.get("/api/v1/health", headers=h)
        r = await c.get("/api/v1/health", headers=h)
    assert r.status_code == 429
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert r.headers["x-frame-options"] == "DENY"


# ------------------------------- AssistantService -------------------------------


@pytest.mark.asyncio
async def test_assistant_falls_back_to_template_answer_when_llm_fails():
    app = create_app(AppSettings())
    swap_assistant(app, FailingLLM())
    async with http(app) as c:
        r = await c.post("/api/v1/assistant/ask", json={"brief": brief(), "question": "budget?"})
    data = r.json()
    assert r.status_code == 200
    assert data["source"] == "template"
    assert "20000.00" in data["answer"] and "100 guests" in data["answer"]


@pytest.mark.asyncio
async def test_assistant_returns_refusal_when_parsed_answer_is_empty(monkeypatch):
    app = create_app(AppSettings())
    swap_assistant(app, ScriptedLLM("anything"))
    monkeypatch.setattr("eventcraft.services.assistant.parse_assistant_response", lambda _c: "")
    async with http(app) as c:
        r = await c.post("/api/v1/assistant/ask", json={"brief": brief(), "question": "poem?"})
    assert r.json()["answer"] == OFF_TOPIC_REFUSAL


# ------------------------------- PlannerService ---------------------------------


@pytest.mark.asyncio
async def test_budget_still_sums_exactly_when_llm_is_down():
    app = create_app(AppSettings())
    swap_planner(app, FailingLLM())
    payload = {"event_type": "wedding", "budget_total": "75000.00", "currency": "INR",
               "guest_count": 120, "priorities": [], "contingency_percent": "6.00"}
    async with http(app) as c:
        r = await c.post("/api/v1/budget/rebalance", json=payload)
    assert r.status_code == 200
    assert sum(Decimal(x["amount"]) for x in r.json()["lines"]) == Decimal("75000.00")


@pytest.mark.asyncio
async def test_ideas_fall_back_to_five_templates_when_llm_returns_garbage():
    app = create_app(AppSettings())
    swap_planner(app, ScriptedLLM("this is not json"))
    async with http(app) as c:
        r = await c.post("/api/v1/plans/ideas", json={"brief": brief(), "steer": "jazz"})
    assert r.status_code == 200
    assert len(r.json()["ideas"]) == 5


@pytest.mark.asyncio
async def test_identical_ideas_requests_hit_the_cache_instead_of_the_llm():
    app = create_app(AppSettings())
    llm = ScriptedLLM("not json")
    swap_planner(app, llm)
    body = {"brief": brief(), "steer": "jazz"}
    async with http(app) as c:
        await c.post("/api/v1/plans/ideas", json=body)
        await c.post("/api/v1/plans/ideas", json=body)
    assert llm.calls == 1
