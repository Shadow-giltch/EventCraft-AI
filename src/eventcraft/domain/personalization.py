"""Pure domain logic for deriving planning signals from user inputs."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

INTIMATE_MAX = 30
MEDIUM_MAX = 100
LARGE_MAX = 300

URGENT_DAYS = 30
MODERATE_DAYS = 120


@dataclass(frozen=True)
class PersonalizationSignals:
    """Computed signals driving both LLM prompts and deterministic fallbacks."""

    guest_size_band: str
    lead_time_band: str
    children_present: bool
    seniors_present: bool
    priorities: list[str] = field(default_factory=list)
    dietary_needs: list[str] = field(default_factory=list)
    accessibility_needs: list[str] = field(default_factory=list)
    culture: str = ""
    interests: list[str] = field(default_factory=list)
    style: str = ""


def derive_guest_band(count: int) -> str:
    """Determine guest size category from head count."""
    if count < INTIMATE_MAX:
        return "intimate"
    if count <= MEDIUM_MAX:
        return "medium"
    if count <= LARGE_MAX:
        return "large"
    return "mega"


def derive_lead_band(days: int) -> str:
    """Determine lead-time band from days remaining to event."""
    if days < URGENT_DAYS:
        return "urgent"
    if days <= MODERATE_DAYS:
        return "moderate"
    return "relaxed"


def extract_signals(
    guest_count: int,
    event_date: date,
    today: date,
    context: Mapping[str, object] | None = None,
) -> PersonalizationSignals:
    """Extract structured personalization signals from event parameters."""
    lead_days = max(0, (event_date - today).days)
    guest_band = derive_guest_band(guest_count)
    lead_band = derive_lead_band(lead_days)

    ctx = context or {}
    raw_prio = ctx.get("priorities")
    raw_diet = ctx.get("dietary_needs")
    raw_acc = ctx.get("accessibility_needs")
    raw_int = ctx.get("interests")

    def _as_seq(val: object) -> Sequence[object]:
        return val if isinstance(val, Sequence) and not isinstance(val, (str, bytes)) else ()

    clean_priorities = [str(p).strip() for p in _as_seq(raw_prio) if str(p).strip()]
    clean_dietary = [str(d).strip() for d in _as_seq(raw_diet) if str(d).strip()]
    clean_access = [str(a).strip() for a in _as_seq(raw_acc) if str(a).strip()]
    clean_interests = [str(i).strip() for i in _as_seq(raw_int) if str(i).strip()]

    return PersonalizationSignals(
        guest_size_band=guest_band,
        lead_time_band=lead_band,
        children_present=bool(ctx.get("children_present", False)),
        seniors_present=bool(ctx.get("seniors_present", False)),
        priorities=clean_priorities,
        dietary_needs=clean_dietary,
        accessibility_needs=clean_access,
        culture=str(ctx.get("culture", "")).strip(),
        interests=clean_interests,
        style=str(ctx.get("style", "")).strip(),
    )
