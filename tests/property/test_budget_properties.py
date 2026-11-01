from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from eventcraft.domain.budget import CategoryConfig, allocate_budget

sample_configs = [
    CategoryConfig("Venue", Decimal("40.0"), Decimal("15.0"), Decimal("60.0"), "Space", "Tip"),
    CategoryConfig("Catering", Decimal("35.0"), Decimal("15.0"), Decimal("50.0"), "Food", "Tip"),
    CategoryConfig("Photo", Decimal("20.0"), Decimal("5.0"), Decimal("30.0"), "Pictures", "Tip"),
]


@settings(max_examples=50)
@given(
    total=st.decimals(min_value=Decimal("100.00"), max_value=Decimal("10000000.00"), places=2),
    guests=st.integers(min_value=1, max_value=5000),
    contingency=st.decimals(min_value=Decimal("3.00"), max_value=Decimal("15.00"), places=2),
)
def test_budget_exact_sum_and_non_negative(total: Decimal, guests: int, contingency: Decimal):
    plan = allocate_budget(
        total_amount=total,
        currency="USD",
        guest_count=guests,
        configs=sample_configs,
        contingency_percent=contingency,
    )
    allocated_sum = sum(line.amount for line in plan.lines)
    assert allocated_sum == total
    for line in plan.lines:
        assert line.amount >= Decimal("0.00")
