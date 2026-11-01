"""Pure domain package containing business logic with zero framework or I/O dependencies."""

from eventcraft.domain.budget import (
    BudgetLine,
    BudgetPlan,
    CategoryConfig,
    allocate_budget,
)
from eventcraft.domain.clock import Clock, FixedClock, SystemClock
from eventcraft.domain.ideas import (
    IdeaItem,
    PersonalizedIdeasPlan,
    build_deterministic_ideas,
)
from eventcraft.domain.personalization import (
    PersonalizationSignals,
    extract_signals,
)
from eventcraft.domain.timeline import (
    Milestone,
    MilestoneTemplate,
    RunOfShowItem,
    TimelinePlan,
    schedule_timeline,
)
from eventcraft.domain.vendors import (
    VendorChecklistPlan,
    VendorItem,
    VendorItemTemplate,
    VendorProgressSummary,
    VendorStatus,
    build_vendor_checklist,
    calculate_progress,
)

__all__ = [
    "BudgetLine",
    "BudgetPlan",
    "CategoryConfig",
    "Clock",
    "FixedClock",
    "IdeaItem",
    "Milestone",
    "MilestoneTemplate",
    "PersonalizationSignals",
    "PersonalizedIdeasPlan",
    "RunOfShowItem",
    "SystemClock",
    "TimelinePlan",
    "VendorChecklistPlan",
    "VendorItem",
    "VendorItemTemplate",
    "VendorProgressSummary",
    "VendorStatus",
    "allocate_budget",
    "build_deterministic_ideas",
    "build_vendor_checklist",
    "calculate_progress",
    "extract_signals",
    "schedule_timeline",
]
