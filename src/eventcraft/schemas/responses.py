"""Pydantic v2 response schemas for all planning endpoints."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from eventcraft.domain.vendors import VendorStatus


class GenerationMetadata(BaseModel):
    """Execution metadata detailing source, caching, and latency."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(..., description="Generator source: 'ai' or 'template'.")
    cache: str = Field(..., description="Cache outcome: 'hit' or 'miss'.")
    latency_ms: int = Field(..., description="Generation latency in milliseconds.")
    tokens_used: int | None = Field(default=None, description="Reported token count.")


class BudgetLineResponse(BaseModel):
    """Single budget line allocation."""

    model_config = ConfigDict(extra="forbid")

    category: str
    percent: Decimal
    amount: Decimal
    rationale: str
    saving_tip: str


class BudgetResponse(BaseModel):
    """Budget deliverable response model."""

    model_config = ConfigDict(extra="forbid")

    total_amount: Decimal
    currency: str
    guest_count: int
    cost_per_guest: Decimal
    lines: list[BudgetLineResponse]
    contingency_amount: Decimal
    meta: GenerationMetadata


class MilestoneResponse(BaseModel):
    """Timeline milestone with validated due date."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    phase: str
    due_date: date
    priority: str
    depends_on: list[str]
    notes: str
    is_rush: bool


class RunOfShowResponse(BaseModel):
    """Timed day-of event schedule item."""

    model_config = ConfigDict(extra="forbid")

    time: str
    activity: str
    responsible: str
    notes: str


class TimelineResponse(BaseModel):
    """Timeline deliverable response model."""

    model_config = ConfigDict(extra="forbid")

    event_date: date
    reference_date: date
    total_lead_days: int
    is_rush_schedule: bool
    milestones: list[MilestoneResponse]
    run_of_show: list[RunOfShowResponse]
    meta: GenerationMetadata


class VendorItemResponse(BaseModel):
    """Vendor checklist vetting item."""

    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    title: str
    budget_line: str
    milestone_id: str
    book_by_date: date
    questions_to_ask: list[str]
    documents_to_verify: list[str]
    red_flags: list[str]
    status: VendorStatus


class VendorProgressResponse(BaseModel):
    """Checklist completion progress summary."""

    model_config = ConfigDict(extra="forbid")

    total_items: int
    completed_items: int
    in_progress_items: int
    pending_items: int
    percent_complete: int


class VendorChecklistResponse(BaseModel):
    """Vendor checklist deliverable response model."""

    model_config = ConfigDict(extra="forbid")

    items: list[VendorItemResponse]
    progress: VendorProgressResponse
    meta: GenerationMetadata


class IdeaItemResponse(BaseModel):
    """Personalized concept recommendation."""

    model_config = ConfigDict(extra="forbid")

    facet: str
    title: str
    description: str
    why_it_fits: str
    budget_tier: str


class PersonalizedIdeasResponse(BaseModel):
    """Personalized ideas deliverable response model."""

    model_config = ConfigDict(extra="forbid")

    event_type: str
    steer: str | None
    ideas: list[IdeaItemResponse]
    meta: GenerationMetadata


class FullPlanResponse(BaseModel):
    """Complete multi-deliverable plan generated for the user event brief."""

    model_config = ConfigDict(extra="forbid")

    budget: BudgetResponse
    timeline: TimelineResponse
    vendor_checklist: VendorChecklistResponse
    personalized_ideas: PersonalizedIdeasResponse
    disclaimer: str = Field(
        default="All figures and dates are planning estimates, not guaranteed commercial quotes."
    )


class AssistantAnswerResponse(BaseModel):
    """Response returned by the grounded event planning assistant."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    source: str
    latency_ms: int


class HealthResponse(BaseModel):
    """Health check status response."""

    model_config = ConfigDict(extra="forbid")

    status: str
    timestamp: str
    version: str
