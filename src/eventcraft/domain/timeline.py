"""Pure domain logic for timeline scheduling planned backwards from event date."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

MAX_PLANNING_HORIZON_DAYS = 365 * 3  # 3 years max horizon
MIN_LEAD_DAYS_RUSH_THRESHOLD = 30


@dataclass(frozen=True)
class MilestoneTemplate:
    """Template definition for a milestone with ideal lead days before event."""

    id: str
    title: str
    phase: str
    lead_days: int  # Days before event date in an ideal schedule
    priority: str
    depends_on: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class RunOfShowItem:
    """Detailed time-stamped schedule item for the event day."""

    time: str
    activity: str
    responsible: str
    notes: str


@dataclass(frozen=True)
class Milestone:
    """Calculated milestone with validated due date and dependency status."""

    id: str
    title: str
    phase: str
    due_date: date
    priority: str
    depends_on: list[str]
    notes: str
    is_rush: bool


@dataclass(frozen=True)
class TimelinePlan:
    """Complete timeline deliverable with milestones and day-of run-of-show."""

    event_date: date
    reference_date: date
    total_lead_days: int
    is_rush_schedule: bool
    milestones: list[Milestone]
    run_of_show: list[RunOfShowItem]


def _validate_event_date(target_date: date, today: date) -> None:
    """Validate that target event date is in the future within 3 years."""
    if target_date <= today:
        raise ValueError("Event date must be in the future.")
    delta_days = (target_date - today).days
    if delta_days > MAX_PLANNING_HORIZON_DAYS:
        raise ValueError("Event date cannot be more than 3 years in the future.")


def _calculate_proportional_days(
    ideal_days: int,
    max_ideal: int,
    available_days: int,
) -> int:
    """Scale milestone lead days proportionally if available days are compressed."""
    if available_days >= max_ideal or max_ideal <= 0:
        return ideal_days
    # Proportional compression
    ratio = available_days / max_ideal
    compressed = round(ideal_days * ratio)
    # Never exceed available days, keep non-negative
    return max(0, min(available_days, compressed))


def _resolve_dependencies(
    milestones: list[Milestone],
    today: date,
    event_date: date,
) -> list[Milestone]:
    """Ensure prerequisite milestones are scheduled on or before dependents."""
    adjusted: dict[str, date] = {m.id: m.due_date for m in milestones}

    # Iterate to propagate backwards dependency constraint
    for _ in range(len(milestones)):
        changed = False
        for m in milestones:
            for dep_id in m.depends_on:
                if dep_id in adjusted and adjusted[dep_id] > adjusted[m.id]:
                    adjusted[dep_id] = adjusted[m.id]
                    changed = True
        if not changed:
            break

    result: list[Milestone] = []
    for m in milestones:
        due = max(today, min(event_date, adjusted[m.id]))
        result.append(
            Milestone(
                id=m.id,
                title=m.title,
                phase=m.phase,
                due_date=due,
                priority=m.priority,
                depends_on=m.depends_on,
                notes=m.notes,
                is_rush=m.is_rush or (due == today and m.due_date > today),
            )
        )
    return result


def schedule_timeline(
    event_date: date,
    today: date,
    templates: Sequence[MilestoneTemplate],
    run_of_show: Sequence[RunOfShowItem],
) -> TimelinePlan:
    """Build compressed and dependency-checked timeline backwards from event date."""
    _validate_event_date(event_date, today)
    available_days = (event_date - today).days
    max_ideal = max((t.lead_days for t in templates), default=available_days)
    is_compressed = available_days < max_ideal

    preliminary: list[Milestone] = []
    for t in templates:
        effective_lead = _calculate_proportional_days(t.lead_days, max_ideal, available_days)
        due = event_date - timedelta(days=effective_lead)
        clamped_due = max(today, min(event_date, due))
        is_rush = is_compressed and (t.lead_days > available_days)

        preliminary.append(
            Milestone(
                id=t.id,
                title=t.title,
                phase=t.phase,
                due_date=clamped_due,
                priority=t.priority,
                depends_on=list(t.depends_on),
                notes=t.notes,
                is_rush=is_rush,
            )
        )

    resolved = _resolve_dependencies(preliminary, today, event_date)
    # Sort chronologically by due date, then priority
    prio_order = {"high": 0, "medium": 1, "low": 2}
    resolved.sort(key=lambda m: (m.due_date, prio_order.get(m.priority, 1)))

    return TimelinePlan(
        event_date=event_date,
        reference_date=today,
        total_lead_days=available_days,
        is_rush_schedule=is_compressed,
        milestones=resolved,
        run_of_show=list(run_of_show),
    )
