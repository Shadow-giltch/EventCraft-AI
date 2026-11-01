"""Gap-closing tests for eventcraft.domain.vendors."""

from datetime import date

import pytest

from eventcraft.domain.vendors import (
    VendorItem,
    VendorItemTemplate,
    VendorStatus,
    build_vendor_checklist,
    calculate_progress,
)

D1, D2, D3 = date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1)


def tmpl(id_, category="Cat", milestone="m1"):
    return VendorItemTemplate(
        id=id_,
        category=category,
        title=f"T-{id_}",
        budget_line="Venue",
        milestone_id=milestone,
        questions_to_ask=["q"],
        documents_to_verify=["d"],
        red_flags=["r"],
    )


def item(status):
    return VendorItem(
        id="x", category="c", title="t", budget_line="b", milestone_id="m",
        book_by_date=D1, questions_to_ask=[], documents_to_verify=[], red_flags=[],
        status=status,
    )


def test_progress_empty_checklist_is_100_percent_with_zero_counts():
    p = calculate_progress([])
    assert (p.total_items, p.completed_items, p.in_progress_items, p.pending_items) == (0, 0, 0, 0)
    assert p.percent_complete == 100


def test_progress_counts_each_status_bucket():
    items = [
        item(VendorStatus.TO_DO),
        item(VendorStatus.CONTACTED),
        item(VendorStatus.QUOTE_RECEIVED),
        item(VendorStatus.BOOKED),
        item(VendorStatus.CONFIRMED),
    ]
    p = calculate_progress(items)
    assert (p.total_items, p.pending_items, p.in_progress_items, p.completed_items) == (5, 1, 2, 2)
    assert p.percent_complete == 40


def test_progress_percent_rounds():
    items = [item(VendorStatus.BOOKED)] + [item(VendorStatus.TO_DO)] * 2
    assert calculate_progress(items).percent_complete == 33


def test_checklist_uses_milestone_date_or_falls_back_to_default():
    plan = build_vendor_checklist(
        [tmpl("a", milestone="m1"), tmpl("b", milestone="missing")],
        {"m1": D2},
        default_date=D3,
    )
    dates = {i.id: i.book_by_date for i in plan.items}
    assert dates == {"a": D2, "b": D3}


def test_checklist_status_defaults_and_invalid_values_fall_back_to_to_do():
    plan = build_vendor_checklist(
        [tmpl("a"), tmpl("b"), tmpl("c")],
        {"m1": D1},
        D1,
        current_statuses={"a": "booked", "b": "not-a-status"},
    )
    st = {i.id: i.status for i in plan.items}
    assert st == {"a": VendorStatus.BOOKED, "b": VendorStatus.TO_DO, "c": VendorStatus.TO_DO}
    assert plan.progress.completed_items == 1


def test_checklist_sorted_by_date_then_category():
    plan = build_vendor_checklist(
        [
            tmpl("1", "Zebra", "late"),
            tmpl("2", "Beta", "early"),
            tmpl("3", "Alpha", "early"),
        ],
        {"early": D1, "late": D2},
        D3,
    )
    assert [i.id for i in plan.items] == ["3", "2", "1"]


def test_checklist_copies_lists_so_template_is_not_mutated():
    t = tmpl("a")
    plan = build_vendor_checklist([t], {"m1": D1}, D1)
    plan.items[0].questions_to_ask.append("extra")
    assert t.questions_to_ask == ["q"]


def test_empty_templates_gives_empty_plan():
    plan = build_vendor_checklist([], {}, D1)
    assert plan.items == []
    assert plan.progress.percent_complete == 100


@pytest.mark.parametrize("s", [v.value for v in VendorStatus])
def test_every_valid_status_string_round_trips(s):
    plan = build_vendor_checklist([tmpl("a")], {"m1": D1}, D1, {"a": s})
    assert plan.items[0].status.value == s
