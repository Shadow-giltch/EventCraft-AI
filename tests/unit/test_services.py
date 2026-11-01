import asyncio
from datetime import date
from decimal import Decimal

import pytest

from eventcraft.domain.clock import FixedClock
from eventcraft.knowledge.loader import KnowledgeRepository
from eventcraft.llm.base import LLMResponse
from eventcraft.llm.cache import SingleFlightCache
from eventcraft.schemas.requests import EventBriefRequest
from eventcraft.services.assistant import AssistantService
from eventcraft.services.planner import PlannerService


class BrokenLLMClient:
    async def generate(self, prompt: str, temp: float = 0.2, max_tok: int = 1024) -> LLMResponse:
        raise RuntimeError("LLM network disconnected")


class MalformedLLMClient:
    async def generate(self, prompt: str, temp: float = 0.2, max_tok: int = 1024) -> LLMResponse:
        return LLMResponse("Not valid JSON at all", "ai", 10, None)


@pytest.fixture
def base_brief():
    return EventBriefRequest(
        event_type="wedding",
        event_date=date(2026, 12, 1),
        guest_count=100,
        budget_total=Decimal("20000.00"),
        currency="USD",
        priorities=["Photography & Video"],
    )


@pytest.mark.asyncio
async def test_planner_fallback_on_broken_llm(base_brief):
    kb = KnowledgeRepository.load_from_directory()
    cache = SingleFlightCache()
    clock = FixedClock(date(2026, 6, 1))
    sem = asyncio.Semaphore(5)

    planner = PlannerService(kb, BrokenLLMClient(), cache, clock, sem)
    plan = await planner.generate_full_plan(base_brief)

    assert plan.budget.meta.source == "template"
    assert plan.personalized_ideas.meta.source == "template"
    assert len(plan.personalized_ideas.ideas) == 5


@pytest.mark.asyncio
async def test_planner_fallback_on_malformed_llm(base_brief):
    kb = KnowledgeRepository.load_from_directory()
    cache = SingleFlightCache()
    clock = FixedClock(date(2026, 6, 1))
    sem = asyncio.Semaphore(5)

    planner = PlannerService(kb, MalformedLLMClient(), cache, clock, sem)
    ideas = await planner.generate_ideas(base_brief, base_brief.model_dump(mode="json"))

    assert ideas.meta.source == "template"
    assert len(ideas.ideas) == 5


@pytest.mark.asyncio
async def test_assistant_fallback_on_broken_llm(base_brief):
    kb = KnowledgeRepository.load_from_directory()
    clock = FixedClock(date(2026, 6, 1))
    sem = asyncio.Semaphore(5)

    assistant = AssistantService(kb, BrokenLLMClient(), clock, sem)
    resp = await assistant.answer_question(base_brief, "When is venue booked?", [])

    assert resp.source == "template"
    assert "20000.00" in resp.answer


class MockJsonWrappedLLMClient:
    async def generate(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 1024) -> LLMResponse:
        return LLMResponse('{"response": "Secure your ceremony venue at least 9 months before event day."}', "ai", 15, 20)


class MockPlainTextLLMClient:
    async def generate(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 1024) -> LLMResponse:
        return LLMResponse("Secure your ceremony venue at least 9 months before event day.", "ai", 12, 18)


class MockFencedLLMClient:
    async def generate(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 1024) -> LLMResponse:
        return LLMResponse('```json\n{\n  "response": "Secure your ceremony venue at least 9 months before event day."\n}\n```', "ai", 18, 25)


class MockEmptyLLMClient:
    async def generate(self, prompt: str, temperature: float = 0.2, max_output_tokens: int = 1024) -> LLMResponse:
        return LLMResponse("   ", "ai", 5, 2)


@pytest.mark.asyncio
async def test_assistant_with_json_wrapped_llm_reply(base_brief):
    kb = KnowledgeRepository.load_from_directory()
    clock = FixedClock(date(2026, 6, 1))
    sem = asyncio.Semaphore(5)

    assistant = AssistantService(kb, MockJsonWrappedLLMClient(), clock, sem)
    resp = await assistant.answer_question(base_brief, "What should I book first?", [])

    assert resp.source == "ai"
    assert resp.answer == "Secure your ceremony venue at least 9 months before event day."
    assert "{" not in resp.answer
    assert '"response"' not in resp.answer


@pytest.mark.asyncio
async def test_assistant_with_plain_text_llm_reply(base_brief):
    kb = KnowledgeRepository.load_from_directory()
    clock = FixedClock(date(2026, 6, 1))
    sem = asyncio.Semaphore(5)

    assistant = AssistantService(kb, MockPlainTextLLMClient(), clock, sem)
    resp = await assistant.answer_question(base_brief, "What should I book first?", [])

    assert resp.source == "ai"
    assert resp.answer == "Secure your ceremony venue at least 9 months before event day."


@pytest.mark.asyncio
async def test_assistant_with_fenced_llm_reply(base_brief):
    kb = KnowledgeRepository.load_from_directory()
    clock = FixedClock(date(2026, 6, 1))
    sem = asyncio.Semaphore(5)

    assistant = AssistantService(kb, MockFencedLLMClient(), clock, sem)
    resp = await assistant.answer_question(base_brief, "What should I book first?", [])

    assert resp.source == "ai"
    assert resp.answer == "Secure your ceremony venue at least 9 months before event day."
    assert "```" not in resp.answer


@pytest.mark.asyncio
async def test_assistant_with_empty_llm_reply_falls_back_to_template(base_brief):
    kb = KnowledgeRepository.load_from_directory()
    clock = FixedClock(date(2026, 6, 1))
    sem = asyncio.Semaphore(5)

    assistant = AssistantService(kb, MockEmptyLLMClient(), clock, sem)
    resp = await assistant.answer_question(base_brief, "What should I book first?", [])

    assert resp.source == "template"
    assert "wedding plan" in resp.answer

