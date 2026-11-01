"""Gap-closing tests for eventcraft.domain.budget (largest-remainder allocation)."""

from decimal import Decimal

import pytest

from eventcraft.domain.budget import (
    MAX_CONTINGENCY_PERCENT,
    MIN_CONTINGENCY_PERCENT,
    CategoryConfig,
    allocate_budget,
)


def cfg(name, default="20", lo="5", hi="40"):
    return CategoryConfig(
        name=name,
        default_percent=Decimal(default),
        min_percent=Decimal(lo),
        max_percent=Decimal(hi),
        rationale=f"why {name}",
        saving_tip=f"tip {name}",
    )


CONFIGS = [cfg("Venue", "30"), cfg("Food", "40"), cfg("Decor", "15"), cfg("Music", "15")]


def line(plan, name):
    return next(x for x in plan.lines if x.category == name)


def total_of(plan):
    return sum(x.amount for x in plan.lines)


# ---- validation -----------------------------------------------------------------


@pytest.mark.parametrize("bad_total", [Decimal("0"), Decimal("0.00"), Decimal("-1")])
def test_rejects_non_positive_total(bad_total):
    with pytest.raises(ValueError, match="greater than zero"):
        allocate_budget(bad_total, "USD", 10, CONFIGS)


@pytest.mark.parametrize("bad_guests", [0, -3])
def test_rejects_guest_count_below_one(bad_guests):
    with pytest.raises(ValueError, match="at least 1"):
        allocate_budget(Decimal("100"), "USD", bad_guests, CONFIGS)


# ---- the core invariant: cents always sum exactly --------------------------------


@pytest.mark.parametrize(
    "total",
    ["0.01", "0.02", "0.07", "1.00", "99.99", "100.01", "12345.67", "99999999.99"],
)
@pytest.mark.parametrize("contingency", ["3", "5", "7.5", "15"])
def test_line_amounts_always_sum_to_total(total, contingency):
    plan = allocate_budget(
        Decimal(total), "USD", 7, CONFIGS, contingency_percent=Decimal(contingency)
    )
    assert total_of(plan) == Decimal(total)


def test_no_line_is_negative_and_amounts_have_two_decimals():
    plan = allocate_budget(Decimal("33.33"), "USD", 3, CONFIGS)
    for x in plan.lines:
        assert x.amount >= 0
        assert x.amount == x.amount.quantize(Decimal("0.01"))


def test_contingency_is_last_line_and_matches_plan_field():
    plan = allocate_budget(Decimal("1000"), "USD", 10, CONFIGS)
    assert plan.lines[-1].category == "Contingency Fund"
    assert plan.lines[-1].amount == plan.contingency_amount
    assert plan.contingency_amount == Decimal("50.00")  # default 5%


def test_tie_on_remainder_goes_to_earliest_category():
    # 1 cent, two identical categories: the single cent must go to the first one.
    configs = [cfg("A", "50", "1", "99"), cfg("B", "50", "1", "99")]
    plan = allocate_budget(Decimal("0.01"), "USD", 1, configs)
    assert line(plan, "A").amount == Decimal("0.01")
    assert line(plan, "B").amount == Decimal("0.00")
    assert line(plan, "Contingency Fund").amount == Decimal("0.00")


# ---- contingency clamping --------------------------------------------------------


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        ("0", MIN_CONTINGENCY_PERCENT),
        ("1.5", MIN_CONTINGENCY_PERCENT),
        ("50", MAX_CONTINGENCY_PERCENT),
        ("100", MAX_CONTINGENCY_PERCENT),
    ],
)
def test_contingency_percent_is_clamped(requested, expected):
    plan = allocate_budget(
        Decimal("10000"), "USD", 10, CONFIGS, contingency_percent=Decimal(requested)
    )
    assert plan.contingency_amount == Decimal("10000") * expected / 100


# ---- weights: priorities, custom weights, clamping --------------------------------


def test_priority_boosts_category_share_case_insensitively_and_trims():
    base = allocate_budget(Decimal("10000"), "USD", 10, CONFIGS)
    boosted = allocate_budget(Decimal("10000"), "USD", 10, CONFIGS, priorities=["  DECOR "])
    assert line(boosted, "Decor").amount > line(base, "Decor").amount
    assert line(boosted, "Venue").amount < line(base, "Venue").amount


def test_priority_boost_is_clamped_to_max_percent():
    configs = [cfg("Food", "39", "5", "40"), cfg("Other", "30", "5", "40")]
    plan = allocate_budget(Decimal("10000"), "USD", 10, configs, priorities=["food"])
    # 39 + 3 = 42 -> clamped to 40, so Food:Other weight ratio is 40:30
    ratio = line(plan, "Food").amount / line(plan, "Other").amount
    assert round(ratio, 2) == round(Decimal(40) / Decimal(30), 2)


def test_unknown_priority_is_ignored():
    base = allocate_budget(Decimal("10000"), "USD", 10, CONFIGS)
    plan = allocate_budget(Decimal("10000"), "USD", 10, CONFIGS, priorities=["nonexistent"])
    assert [x.amount for x in plan.lines] == [x.amount for x in base.lines]


def test_custom_weight_overrides_default_and_skips_priority_boost():
    plan = allocate_budget(
        Decimal("10000"),
        "USD",
        10,
        CONFIGS,
        priorities=["Venue"],
        custom_weights={"Venue": Decimal("10")},
    )
    # Venue weight is 10 (custom, no +3 boost) vs Food 40
    assert line(plan, "Food").amount > 3 * line(plan, "Venue").amount


@pytest.mark.parametrize(("custom", "clamped_to"), [("1", "5"), ("99", "40")])
def test_custom_weight_is_clamped_to_category_bounds(custom, clamped_to):
    configs = [cfg("X", "20", "5", "40"), cfg("Y", "20", "5", "40")]
    got = allocate_budget(
        Decimal("10000"), "USD", 1, configs, custom_weights={"X": Decimal(custom)}
    )
    expected = allocate_budget(
        Decimal("10000"), "USD", 1, configs, custom_weights={"X": Decimal(clamped_to)}
    )
    assert [x.amount for x in got.lines] == [x.amount for x in expected.lines]


def test_custom_weights_for_unknown_category_are_ignored():
    base = allocate_budget(Decimal("500"), "USD", 5, CONFIGS)
    plan = allocate_budget(Decimal("500"), "USD", 5, CONFIGS, custom_weights={"Ghost": Decimal(9)})
    assert [x.amount for x in plan.lines] == [x.amount for x in base.lines]


# ---- degenerate configs ----------------------------------------------------------


def test_zero_total_weight_puts_everything_in_contingency_bucket_without_crashing():
    zero = [cfg("A", "0", "0", "0"), cfg("B", "0", "0", "0")]
    plan = allocate_budget(Decimal("100.00"), "USD", 4, zero)
    assert total_of(plan) == Decimal("100.00")
    assert line(plan, "A").amount + line(plan, "B").amount <= Decimal("100.00")


def test_empty_config_list_still_returns_contingency_only_plan():
    plan = allocate_budget(Decimal("100.00"), "USD", 4, [])
    assert [x.category for x in plan.lines] == ["Contingency Fund"]
    assert plan.lines[0].amount == Decimal("100.00")


# ---- metadata --------------------------------------------------------------------


def test_currency_uppercased_and_rationale_copied():
    plan = allocate_budget(Decimal("100"), "inr", 4, CONFIGS)
    assert plan.currency == "INR"
    assert line(plan, "Venue").rationale == "why Venue"
    assert line(plan, "Venue").saving_tip == "tip Venue"


@pytest.mark.parametrize(
    ("total", "guests", "expected"),
    [("100", 3, "33.33"), ("200", 3, "66.67"), ("0.01", 2, "0.01"), ("10", 4, "2.50")],
)
def test_cost_per_guest_rounds_half_up(total, guests, expected):
    plan = allocate_budget(Decimal(total), "USD", guests, CONFIGS)
    assert plan.cost_per_guest == Decimal(expected)


def test_total_amount_is_quantized_to_cents():
    plan = allocate_budget(Decimal("100"), "USD", 1, CONFIGS)
    assert str(plan.total_amount) == "100.00"
