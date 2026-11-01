"""Gap-closing tests for eventcraft.domain.timeline."""

from datetime import date, timedelta

import pytest

from eventcraft.domain.timeline import (
    MAX_PLANNING_HORIZON_DAYS,
    MilestoneTemplate,
    RunOfShowItem,
    _calculate_proportional_days,
    schedule_timeline,
)

TODAY = date(2026, 1, 1)


def mt(id_, lead, priority="medium", depends_on=None, title=None):
    return MilestoneTemplate(
        id=id_,
        title=title or id_,
        phase="p",
        lead_days=lead,
        priority=priority,
        depends_on=depends_on or [],
    )


def by_id(plan, id_):
    return next(m for m in plan.milestones if m.id == id_)


# ---- event date validation -------------------------------------------------------


@pytest.mark.parametrize("delta", [0, -1, -400])
def test_event_today_or_past_rejected(delta):
    with pytest.raises(ValueError, match="in the future"):
        schedule_timeline(TODAY + timedelta(days=delta), TODAY, [mt("a", 10)], [])


def test_event_beyond_three_years_rejected_but_boundary_allowed():
    ok = schedule_timeline(TODAY + timedelta(days=MAX_PLANNING_HORIZON_DAYS), TODAY, [mt("a", 10)], [])
    assert ok.total_lead_days == MAX_PLANNING_HORIZON_DAYS
    with pytest.raises(ValueError, match="3 years"):
        schedule_timeline(
            TODAY + timedelta(days=MAX_PLANNING_HORIZON_DAYS + 1), TODAY, [mt("a", 10)], []
        )


# ---- proportional compression helper ---------------------------------------------


@pytest.mark.parametrize(
    ("ideal", "max_ideal", "available", "expected"),
    [
        (30, 60, 100, 30),  # plenty of time: untouched
        (30, 60, 60, 30),  # exactly enough
        (30, 60, 30, 15),  # half the time -> half the lead
        (60, 60, 10, 10),  # never exceeds available
        (30, 0, 5, 30),  # max_ideal <= 0 guard
        (0, 60, 10, 0),  # zero lead stays zero
    ],
)
def test_calculate_proportional_days(ideal, max_ideal, available, expected):
    assert _calculate_proportional_days(ideal, max_ideal, available) == expected


# ---- scheduling ------------------------------------------------------------------


def test_uncompressed_schedule_uses_exact_lead_days_and_no_rush():
    event = TODAY + timedelta(days=200)
    plan = schedule_timeline(event, TODAY, [mt("a", 100), mt("b", 30)], [])
    assert plan.is_rush_schedule is False
    assert by_id(plan, "a").due_date == event - timedelta(days=100)
    assert by_id(plan, "b").due_date == event - timedelta(days=30)
    assert not any(m.is_rush for m in plan.milestones)


def test_compressed_schedule_flags_rush_and_never_schedules_in_the_past():
    event = TODAY + timedelta(days=20)
    plan = schedule_timeline(event, TODAY, [mt("a", 100), mt("b", 50), mt("c", 10)], [])
    assert plan.is_rush_schedule is True
    assert plan.total_lead_days == 20
    assert all(TODAY <= m.due_date <= event for m in plan.milestones)
    assert by_id(plan, "a").is_rush and by_id(plan, "b").is_rush
    assert not by_id(plan, "c").is_rush  # 10 <= 20 available


def test_dependency_is_pulled_forward_to_on_or_before_dependent():
    event = TODAY + timedelta(days=300)
    # b needs a, but a (lead 10) would naturally land AFTER b (lead 200)
    plan = schedule_timeline(event, TODAY, [mt("a", 10), mt("b", 200, depends_on=["a"])], [])
    assert by_id(plan, "a").due_date <= by_id(plan, "b").due_date


def test_dependency_chain_propagates_transitively():
    event = TODAY + timedelta(days=300)
    plan = schedule_timeline(
        event,
        TODAY,
        [mt("a", 10), mt("b", 20, depends_on=["a"]), mt("c", 250, depends_on=["b"])],
        [],
    )
    a, b, c = (by_id(plan, i).due_date for i in "abc")
    assert a <= b <= c


def test_unknown_dependency_id_is_ignored():
    event = TODAY + timedelta(days=100)
    plan = schedule_timeline(event, TODAY, [mt("a", 30, depends_on=["ghost"])], [])
    assert by_id(plan, "a").due_date == event - timedelta(days=30)


def test_dependency_pull_to_today_marks_milestone_rush():
    event = TODAY + timedelta(days=100)
    plan = schedule_timeline(event, TODAY, [mt("a", 10), mt("b", 100, depends_on=["a"])], [])
    a = by_id(plan, "a")
    assert a.due_date == TODAY
    assert a.is_rush is True


def test_empty_templates_yield_empty_milestones_but_keep_run_of_show():
    ros = [RunOfShowItem(time="10:00", activity="Doors", responsible="Host", notes="")]
    plan = schedule_timeline(TODAY + timedelta(days=30), TODAY, [], ros)
    assert plan.milestones == []
    assert plan.run_of_show == ros
    assert plan.is_rush_schedule is False


def test_sorted_by_date_then_priority_with_unknown_priority_treated_as_medium():
    event = TODAY + timedelta(days=100)
    plan = schedule_timeline(
        event,
        TODAY,
        [
            mt("low", 50, "low"),
            mt("weird", 50, "urgent!!"),
            mt("high", 50, "high"),
            mt("early", 90, "low"),
        ],
        [],
    )
    assert [m.id for m in plan.milestones] == ["early", "high", "weird", "low"]


def test_templates_and_depends_on_lists_are_not_aliased():
    tmpl = mt("b", 10, depends_on=["a"])
    plan = schedule_timeline(TODAY + timedelta(days=50), TODAY, [mt("a", 5), tmpl], [])
    by_id(plan, "b").depends_on.append("zzz")
    assert tmpl.depends_on == ["a"]
