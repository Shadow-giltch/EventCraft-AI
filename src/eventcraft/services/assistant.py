"""Grounded event assistant service rebuilding context server-side."""

import asyncio
import time
from collections.abc import Sequence

from eventcraft.domain.budget import allocate_budget
from eventcraft.domain.clock import Clock
from eventcraft.domain.timeline import schedule_timeline
from eventcraft.knowledge.loader import KnowledgeRepository
from eventcraft.llm.base import LLMClient
from eventcraft.llm.parsing import parse_assistant_response
from eventcraft.llm.prompts import (
    OFF_TOPIC_REFUSAL,
    build_assistant_prompt,
)
from eventcraft.schemas.requests import EventBriefRequest
from eventcraft.schemas.responses import AssistantAnswerResponse


class AssistantService:
    """Provides grounded conversational answers derived strictly from server-side facts."""

    def __init__(
        self,
        knowledge: KnowledgeRepository,
        llm: LLMClient,
        clock: Clock,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Initialize assistant service with dependencies."""
        self._knowledge = knowledge
        self._llm = llm
        self._clock = clock
        self._semaphore = semaphore

    def _rebuild_grounded_summary(self, brief: EventBriefRequest) -> str:
        """Deterministically reconstruct verified plan facts server-side."""
        kb = self._knowledge.get(brief.event_type)
        budget = allocate_budget(
            total_amount=brief.budget_total,
            currency=brief.currency,
            guest_count=brief.guest_count,
            configs=kb.budget_categories,
            priorities=brief.priorities,
        )
        timeline = schedule_timeline(
            event_date=brief.event_date,
            today=self._clock.today(),
            templates=kb.milestones,
            run_of_show=kb.run_of_show,
        )

        lines_summary = ", ".join(
            f"{line.category}: {line.percent}% ({line.amount} {budget.currency})"
            for line in budget.lines
        )
        milestones_summary = "; ".join(
            f"{m.title} due {m.due_date}" for m in timeline.milestones[:5]
        )

        culture_info = brief.culture_or_tradition or "Not specified"
        style_info = brief.style or "Not specified"

        return (
            f"Event Type: {brief.event_type}\n"
            f"Event Date: {brief.event_date} (Lead days: {timeline.total_lead_days})\n"
            f"Guest Count: {brief.guest_count}\n"
            f"Total Budget: {budget.total_amount} {budget.currency} "
            f"(Cost per guest: {budget.cost_per_guest})\n"
            f"Budget Allocations: {lines_summary}\n"
            f"Key Milestone Deadlines: {milestones_summary}\n"
            f"Priorities: {', '.join(brief.priorities) or 'Balanced'}\n"
            f"Culture/Style: {culture_info} / {style_info}"
        )

    async def answer_question(
        self,
        brief: EventBriefRequest,
        question: str,
        chat_history: Sequence[tuple[str, str]],
    ) -> AssistantAnswerResponse:
        """Generate safe, grounded answer for the given event inquiry."""
        start_t = time.monotonic()
        grounded_context = self._rebuild_grounded_summary(brief)
        prompt = build_assistant_prompt(grounded_context, question, chat_history)

        try:
            async with self._semaphore:
                llm_resp = await self._llm.generate(prompt, temperature=0.2, max_output_tokens=300)
            answer_text = parse_assistant_response(llm_resp.content)
            source = llm_resp.source
        except Exception:
            answer_text = (
                f"Based on your {brief.event_type} plan, your budget total is "
                f"{brief.budget_total} {brief.currency} for {brief.guest_count} guests "
                f"scheduled on {brief.event_date}."
            )
            source = "template"

        if not answer_text:
            answer_text = OFF_TOPIC_REFUSAL

        elapsed = int((time.monotonic() - start_t) * 1000)
        return AssistantAnswerResponse(
            answer=answer_text,
            source=source,
            latency_ms=max(1, elapsed),
        )
