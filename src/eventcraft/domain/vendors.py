"""Pure domain logic for vendor checklists linked to budget and timeline."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum


class VendorStatus(str, Enum):
    """Allowed states for vendor vetting workflow."""

    TO_DO = "to_do"
    CONTACTED = "contacted"
    QUOTE_RECEIVED = "quote_received"
    BOOKED = "booked"
    CONFIRMED = "confirmed"


@dataclass(frozen=True)
class VendorItemTemplate:
    """Knowledge-base template for vendor vetting requirements."""

    id: str
    category: str
    title: str
    budget_line: str
    milestone_id: str
    questions_to_ask: list[str]
    documents_to_verify: list[str]
    red_flags: list[str]


@dataclass(frozen=True)
class VendorItem:
    """Actionable vendor evaluation item with deadline and current status."""

    id: str
    category: str
    title: str
    budget_line: str
    milestone_id: str
    book_by_date: date
    questions_to_ask: list[str]
    documents_to_verify: list[str]
    red_flags: list[str]
    status: VendorStatus = VendorStatus.TO_DO


@dataclass(frozen=True)
class VendorProgressSummary:
    """Aggregate completion metrics across vendor checklist items."""

    total_items: int
    completed_items: int
    in_progress_items: int
    pending_items: int
    percent_complete: int


@dataclass(frozen=True)
class VendorChecklistPlan:
    """Complete vendor checklist deliverable with status and progress metrics."""

    items: list[VendorItem]
    progress: VendorProgressSummary


def calculate_progress(items: Sequence[VendorItem]) -> VendorProgressSummary:
    """Compute aggregate progress counts from current item statuses."""
    total = len(items)
    if total == 0:
        return VendorProgressSummary(0, 0, 0, 0, 100)

    completed = sum(1 for i in items if i.status in (VendorStatus.BOOKED, VendorStatus.CONFIRMED))
    in_progress = sum(
        1 for i in items if i.status in (VendorStatus.CONTACTED, VendorStatus.QUOTE_RECEIVED)
    )
    pending = sum(1 for i in items if i.status == VendorStatus.TO_DO)
    percent = round((completed / total) * 100)

    return VendorProgressSummary(
        total_items=total,
        completed_items=completed,
        in_progress_items=in_progress,
        pending_items=pending,
        percent_complete=percent,
    )


def build_vendor_checklist(
    templates: Sequence[VendorItemTemplate],
    milestone_due_dates: Mapping[str, date],
    default_date: date,
    current_statuses: Mapping[str, str] | None = None,
) -> VendorChecklistPlan:
    """Build checklist items linked to milestone deadlines with current statuses."""
    items: list[VendorItem] = []
    status_map = current_statuses or {}

    for tmpl in templates:
        due_date = milestone_due_dates.get(tmpl.milestone_id, default_date)
        raw_status = status_map.get(tmpl.id, VendorStatus.TO_DO.value)
        try:
            status = VendorStatus(raw_status)
        except ValueError:
            status = VendorStatus.TO_DO

        items.append(
            VendorItem(
                id=tmpl.id,
                category=tmpl.category,
                title=tmpl.title,
                budget_line=tmpl.budget_line,
                milestone_id=tmpl.milestone_id,
                book_by_date=due_date,
                questions_to_ask=list(tmpl.questions_to_ask),
                documents_to_verify=list(tmpl.documents_to_verify),
                red_flags=list(tmpl.red_flags),
                status=status,
            )
        )

    # Sort by book_by_date then category
    items.sort(key=lambda item: (item.book_by_date, item.category))
    progress = calculate_progress(items)

    return VendorChecklistPlan(items=items, progress=progress)
