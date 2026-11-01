"""Thin FastAPI routers delegating business logic to injected services."""

import time
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from eventcraft.domain.budget import allocate_budget
from eventcraft.knowledge.loader import KnowledgeRepository
from eventcraft.schemas.requests import (
    AssistantAskRequest,
    BudgetRebalanceRequest,
    EventBriefRequest,
    RegenerateIdeasRequest,
)
from eventcraft.schemas.responses import (
    AssistantAnswerResponse,
    BudgetLineResponse,
    BudgetResponse,
    FullPlanResponse,
    GenerationMetadata,
    HealthResponse,
    PersonalizedIdeasResponse,
)
from eventcraft.services.assistant import AssistantService
from eventcraft.services.planner import PlannerService

api_router = APIRouter(prefix="/api/v1")


def get_planner_service(request: Request) -> PlannerService:
    """Dependency provider for PlannerService."""
    planner: PlannerService = request.app.state.planner_service
    return planner


def get_assistant_service(request: Request) -> AssistantService:
    """Dependency provider for AssistantService."""
    assistant: AssistantService = request.app.state.assistant_service
    return assistant


def get_knowledge_repo(request: Request) -> KnowledgeRepository:
    """Dependency provider for KnowledgeRepository."""
    repo: KnowledgeRepository = request.app.state.knowledge_repo
    return repo


@api_router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint reporting operational status."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
    )


@api_router.post("/plans/generate", response_model=FullPlanResponse, tags=["Plans"])
async def generate_plan(
    brief: EventBriefRequest,
    planner: Annotated[PlannerService, Depends(get_planner_service)],
) -> FullPlanResponse:
    """Generate complete four-deliverable event plan."""
    return await planner.generate_full_plan(brief)


@api_router.post("/plans/ideas", response_model=PersonalizedIdeasResponse, tags=["Plans"])
async def regenerate_ideas(
    payload: RegenerateIdeasRequest,
    planner: Annotated[PlannerService, Depends(get_planner_service)],
) -> PersonalizedIdeasResponse:
    """Regenerate personalized ideas with optional user steer."""
    canonical = payload.brief.model_dump(mode="json")
    return await planner.generate_ideas(payload.brief, canonical, steer=payload.steer)


@api_router.post("/budget/rebalance", response_model=BudgetResponse, tags=["Budget"])
async def rebalance_budget(
    payload: BudgetRebalanceRequest,
    knowledge: Annotated[KnowledgeRepository, Depends(get_knowledge_repo)],
) -> BudgetResponse:
    """Rebalance budget allocations with exact penny sums using zero LLM tokens."""
    start_t = time.monotonic()
    kb = knowledge.get(payload.event_type)

    domain_plan = allocate_budget(
        total_amount=payload.budget_total,
        currency=payload.currency,
        guest_count=payload.guest_count,
        configs=kb.budget_categories,
        priorities=payload.priorities,
        custom_weights=payload.custom_weights,
        contingency_percent=payload.contingency_percent,
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
            source="template",
            cache="hit",
            latency_ms=max(1, elapsed),
            tokens_used=0,
        ),
    )


@api_router.post("/assistant/ask", response_model=AssistantAnswerResponse, tags=["Assistant"])
async def ask_assistant(
    payload: AssistantAskRequest,
    assistant: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantAnswerResponse:
    """Ask grounded planning assistant regarding the specific event details."""
    return await assistant.answer_question(payload.brief, payload.question, payload.chat_history)
