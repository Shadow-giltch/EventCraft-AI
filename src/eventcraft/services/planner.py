"""Planner orchestration service assembling deliverables from domain and LLM layers."""

import asyncio
import time
from decimal import Decimal
from typing import Any

from eventcraft.domain.budget import allocate_budget
from eventcraft.domain.clock import Clock
from eventcraft.domain.ideas import FACETS, IdeaItem, build_deterministic_ideas
from eventcraft.domain.personalization import extract_signals
from eventcraft.domain.timeline import schedule_timeline
from eventcraft.domain.vendors import build_vendor_checklist
from eventcraft.knowledge.loader import KnowledgeRepository
from eventcraft.llm.base import LLMClient, LLMResponse
from eventcraft.llm.cache import SingleFlightCache
from eventcraft.llm.offline import OfflineClient
from eventcraft.llm.parsing import parse_and_repair_json
from eventcraft.llm.prompts import (
    PROMPT_VERSION,
    build_budget_weights_prompt,
    build_ideas_prompt,
)
from eventcraft.schemas.requests import EventBriefRequest
from eventcraft.schemas.responses import (
    BudgetLineResponse,
    BudgetResponse,
    FullPlanResponse,
    GenerationMetadata,
    IdeaItemResponse,
    MilestoneResponse,
    PersonalizedIdeasResponse,
    RunOfShowResponse,
    TimelineResponse,
    VendorChecklistResponse,
    VendorItemResponse,
    VendorProgressResponse,
)


class PlannerService:
    """Orchestrates multi-section plan creation with caching and fallbacks."""

    def __init__(
        self,
        knowledge: KnowledgeRepository,
        llm: LLMClient,
        cache: SingleFlightCache,
        clock: Clock,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Initialize planner service with injected infrastructure components."""
        self._knowledge = knowledge
        self._llm = llm
        self._cache = cache
        self._clock = clock
        self._semaphore = semaphore
        self._model = "gemini-3.5-flash-lite"

    async def _safe_llm_call(self, prompt: str, temp: float, max_tok: int) -> LLMResponse:
        """Execute LLM call within concurrency limit, falling back cleanly on error."""
        try:
            async with self._semaphore:
                return await self._llm.generate(prompt, temp, max_tok)
        except Exception:
            return await OfflineClient().generate(prompt, temp, max_tok)

    async def generate_budget(
        self, brief: EventBriefRequest, canonical: dict[str, Any]
    ) -> BudgetResponse:
        """Create budget with AI-adjusted weights and exact penny allocation."""
        start_t = time.monotonic()
        kb = self._knowledge.get(brief.event_type)
        ctx = {
            "priorities": brief.priorities,
            "culture": brief.culture_or_tradition,
            "style": brief.style,
        }
        signals = extract_signals(brief.guest_count, brief.event_date, self._clock.today(), ctx)

        categories = [c.name for c in kb.budget_categories]
        prompt = build_budget_weights_prompt(categories, signals)
        cache_key = self._cache.compute_cache_key(canonical, "budget", PROMPT_VERSION, self._model)

        llm_resp, cache_status = await self._cache.get_or_compute(
            cache_key, lambda: self._safe_llm_call(prompt, 0.2, 512)
        )

        weights: dict[str, Decimal] = {}
        source = llm_resp.source
        try:
            parsed = parse_and_repair_json(llm_resp.content)
            raw_weights = parsed.get("weights", {})
            if isinstance(raw_weights, dict):
                for k, v in raw_weights.items():
                    weights[str(k)] = Decimal(str(v))
        except Exception:
            source = "template"

        domain_plan = allocate_budget(
            total_amount=brief.budget_total,
            currency=brief.currency,
            guest_count=brief.guest_count,
            configs=kb.budget_categories,
            priorities=brief.priorities,
            custom_weights=weights if weights else None,
        )

        elapsed = int((time.monotonic() - start_t) * 1000)
        lines = [
            BudgetLineResponse(
                category=line.category,
                percent=line.percent,
                amount=line.amount,
                rationale=line.rationale,
                saving_tip=line.saving_tip,
            )
            for line in domain_plan.lines
        ]

        return BudgetResponse(
            total_amount=domain_plan.total_amount,
            currency=domain_plan.currency,
            guest_count=domain_plan.guest_count,
            cost_per_guest=domain_plan.cost_per_guest,
            lines=lines,
            contingency_amount=domain_plan.contingency_amount,
            meta=GenerationMetadata(
                source=source,
                cache=cache_status,
                latency_ms=max(1, elapsed),
                tokens_used=llm_resp.tokens_used,
            ),
        )

    def generate_timeline(self, brief: EventBriefRequest) -> TimelineResponse:
        """Create timeline with backwards scheduling and dependency enforcement."""
        start_t = time.monotonic()
        kb = self._knowledge.get(brief.event_type)
        domain_timeline = schedule_timeline(
            event_date=brief.event_date,
            today=self._clock.today(),
            templates=kb.milestones,
            run_of_show=kb.run_of_show,
        )

        elapsed = int((time.monotonic() - start_t) * 1000)
        milestones = [
            MilestoneResponse(
                id=m.id,
                title=m.title,
                phase=m.phase,
                due_date=m.due_date,
                priority=m.priority,
                depends_on=m.depends_on,
                notes=m.notes,
                is_rush=m.is_rush,
            )
            for m in domain_timeline.milestones
        ]
        ros = [
            RunOfShowResponse(
                time=r.time,
                activity=r.activity,
                responsible=r.responsible,
                notes=r.notes,
            )
            for r in domain_timeline.run_of_show
        ]

        return TimelineResponse(
            event_date=domain_timeline.event_date,
            reference_date=domain_timeline.reference_date,
            total_lead_days=domain_timeline.total_lead_days,
            is_rush_schedule=domain_timeline.is_rush_schedule,
            milestones=milestones,
            run_of_show=ros,
            meta=GenerationMetadata(
                source="template",
                cache="hit",
                latency_ms=max(1, elapsed),
                tokens_used=None,
            ),
        )

    def generate_vendor_checklist(
        self, brief: EventBriefRequest, timeline: TimelineResponse
    ) -> VendorChecklistResponse:
        """Create vendor checklist linked to timeline deadlines and budget lines."""
        start_t = time.monotonic()
        kb = self._knowledge.get(brief.event_type)
        due_dates = {m.id: m.due_date for m in timeline.milestones}

        domain_vendors = build_vendor_checklist(
            templates=kb.vendor_categories,
            milestone_due_dates=due_dates,
            default_date=brief.event_date,
        )

        elapsed = int((time.monotonic() - start_t) * 1000)
        items = [
            VendorItemResponse(
                id=v.id,
                category=v.category,
                title=v.title,
                budget_line=v.budget_line,
                milestone_id=v.milestone_id,
                book_by_date=v.book_by_date,
                questions_to_ask=v.questions_to_ask,
                documents_to_verify=v.documents_to_verify,
                red_flags=v.red_flags,
                status=v.status,
            )
            for v in domain_vendors.items
        ]
        prog = domain_vendors.progress

        return VendorChecklistResponse(
            items=items,
            progress=VendorProgressResponse(
                total_items=prog.total_items,
                completed_items=prog.completed_items,
                in_progress_items=prog.in_progress_items,
                pending_items=prog.pending_items,
                percent_complete=prog.percent_complete,
            ),
            meta=GenerationMetadata(
                source="template",
                cache="hit",
                latency_ms=max(1, elapsed),
                tokens_used=None,
            ),
        )

    async def generate_ideas(
        self,
        brief: EventBriefRequest,
        canonical: dict[str, Any],
        steer: str | None = None,
    ) -> PersonalizedIdeasResponse:
        """Create five-facet personalized ideas with optional user steer."""
        start_t = time.monotonic()
        ctx = {
            "priorities": brief.priorities,
            "dietary_needs": brief.dietary_needs,
            "accessibility_needs": brief.accessibility_needs,
            "culture": brief.culture_or_tradition,
            "interests": brief.interests,
            "style": brief.style,
        }
        signals = extract_signals(brief.guest_count, brief.event_date, self._clock.today(), ctx)

        effective_steer = steer or brief.steer
        prompt = build_ideas_prompt(brief.event_type, signals, effective_steer)
        cache_key = self._cache.compute_cache_key(
            {**canonical, "steer": effective_steer or ""},
            "ideas",
            PROMPT_VERSION,
            self._model,
        )

        llm_resp, cache_status = await self._cache.get_or_compute(
            cache_key, lambda: self._safe_llm_call(prompt, 0.7, 1024)
        )

        ideas_list: list[IdeaItem] = []
        source = llm_resp.source
        try:
            parsed = parse_and_repair_json(llm_resp.content)
            raw_ideas = parsed.get("ideas", [])
            if isinstance(raw_ideas, list) and len(raw_ideas) > 0:
                for item in raw_ideas:
                    facet = str(item.get("facet", "")).lower()
                    if facet in FACETS:
                        tier = str(item.get("budget_tier", "moderate")).lower()
                        if tier not in ("budget", "moderate", "premium"):
                            tier = "moderate"
                        ideas_list.append(
                            IdeaItem(
                                facet=facet,
                                title=str(item.get("title", "")),
                                description=str(item.get("description", "")),
                                why_it_fits=str(item.get("why_it_fits", "")),
                                budget_tier=tier,
                            )
                        )
        except Exception:
            source = "template"

        if len(ideas_list) < len(FACETS):
            fallback_plan = build_deterministic_ideas(brief.event_type, signals, effective_steer)
            ideas_list = fallback_plan.ideas
            source = "template"

        elapsed = int((time.monotonic() - start_t) * 1000)
        items_resp = [
            IdeaItemResponse(
                facet=i.facet,
                title=i.title,
                description=i.description,
                why_it_fits=i.why_it_fits,
                budget_tier=i.budget_tier,
            )
            for i in ideas_list
        ]

        return PersonalizedIdeasResponse(
            event_type=brief.event_type,
            steer=effective_steer,
            ideas=items_resp,
            meta=GenerationMetadata(
                source=source,
                cache=cache_status,
                latency_ms=max(1, elapsed),
                tokens_used=llm_resp.tokens_used,
            ),
        )

    async def generate_full_plan(self, brief: EventBriefRequest) -> FullPlanResponse:
        """Concurrently generate all four deliverables for the requested event."""
        canonical = brief.model_dump(mode="json")
        b_task = asyncio.create_task(self.generate_budget(brief, canonical))
        i_task = asyncio.create_task(self.generate_ideas(brief, canonical, brief.steer))

        timeline_resp = self.generate_timeline(brief)
        vendors_resp = self.generate_vendor_checklist(brief, timeline_resp)

        budget_resp, ideas_resp = await asyncio.gather(b_task, i_task)

        return FullPlanResponse(
            budget=budget_resp,
            timeline=timeline_resp,
            vendor_checklist=vendors_resp,
            personalized_ideas=ideas_resp,
        )
