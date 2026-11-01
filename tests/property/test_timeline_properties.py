from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from eventcraft.domain.timeline import MilestoneTemplate, schedule_timeline

templates = [
    MilestoneTemplate("m1", "Venue", "Phase 1", 120, "high"),
    MilestoneTemplate("m2", "Invites", "Phase 2", 60, "high", depends_on=["m1"]),
    MilestoneTemplate("m3", "Catering", "Phase 3", 30, "medium", depends_on=["m2"]),
]


@settings(max_examples=50)
@given(
    days_in_future=st.integers(min_value=1, max_value=365 * 2),
)
def test_timeline_due_dates_and_dependency_order(days_in_future: int):
    today = date(2026, 1, 1)
    event_date = today + timedelta(days=days_in_future)
    plan = schedule_timeline(event_date, today, templates, [])

    due_map = {m.id: m.due_date for m in plan.milestones}
    for m in plan.milestones:
        assert m.due_date >= today
        assert m.due_date <= event_date

    assert due_map["m1"] <= due_map["m2"]
    assert due_map["m2"] <= due_map["m3"]
