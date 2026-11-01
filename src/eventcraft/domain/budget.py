"""Pure domain logic for budget allocation using largest-remainder method."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

CENTS_FACTOR = Decimal("100")
ONE_CENT = Decimal("0.01")
ONE_PERCENT = Decimal("0.01")
DEFAULT_CONTINGENCY_PERCENT = Decimal("5.00")
MIN_CONTINGENCY_PERCENT = Decimal("3.00")
MAX_CONTINGENCY_PERCENT = Decimal("15.00")


@dataclass(frozen=True)
class CategoryConfig:
    """Configuration constraints and defaults for a budget category."""

    name: str
    default_percent: Decimal
    min_percent: Decimal
    max_percent: Decimal
    rationale: str
    saving_tip: str


@dataclass(frozen=True)
class BudgetLine:
    """Calculated budget item with exact currency allocation."""

    category: str
    percent: Decimal
    amount: Decimal
    rationale: str
    saving_tip: str


@dataclass(frozen=True)
class BudgetPlan:
    """Complete budget deliverable with totals, lines, and per-guest metrics."""

    total_amount: Decimal
    currency: str
    guest_count: int
    cost_per_guest: Decimal
    lines: list[BudgetLine]
    contingency_amount: Decimal


def _calculate_weights(
    configs: Sequence[CategoryConfig],
    priorities: Sequence[str],
    custom_weights: Mapping[str, Decimal] | None,
) -> dict[str, Decimal]:
    """Calculate clamped and priority-boosted weights for each category."""
    priority_set = {p.strip().lower() for p in priorities}
    raw_weights: dict[str, Decimal] = {}

    for cfg in configs:
        if custom_weights and cfg.name in custom_weights:
            weight = custom_weights[cfg.name]
        else:
            weight = cfg.default_percent
            if cfg.name.lower() in priority_set:
                weight += Decimal("3.00")
        clamped = max(cfg.min_percent, min(cfg.max_percent, weight))
        raw_weights[cfg.name] = clamped

    return raw_weights


def allocate_budget(  # noqa: PLR0913
    total_amount: Decimal,
    currency: str,
    guest_count: int,
    configs: Sequence[CategoryConfig],
    *,
    priorities: Sequence[str] = (),
    custom_weights: Mapping[str, Decimal] | None = None,
    contingency_percent: Decimal = DEFAULT_CONTINGENCY_PERCENT,
) -> BudgetPlan:
    """Allocate budget across categories using largest-remainder method."""
    if total_amount <= Decimal("0.00"):
        raise ValueError("Budget total must be greater than zero.")
    if guest_count < 1:
        raise ValueError("Guest count must be at least 1.")

    clamped_contingency = max(
        MIN_CONTINGENCY_PERCENT, min(MAX_CONTINGENCY_PERCENT, contingency_percent)
    )
    raw_weights = _calculate_weights(configs, priorities, custom_weights)
    total_raw_weight = sum(raw_weights.values())

    contingency_fraction = Fraction(str(clamped_contingency)) / Fraction(100)
    category_pool_fraction = Fraction(1) - contingency_fraction

    # Compute exact fractions summing to 1
    exact_shares: dict[str, Fraction] = {}
    for name, weight in raw_weights.items():
        if total_raw_weight > Decimal("0"):
            weight_frac = Fraction(str(weight)) / Fraction(str(total_raw_weight))
            exact_shares[name] = weight_frac * category_pool_fraction
        else:
            exact_shares[name] = Fraction(0)
    exact_shares["Contingency Fund"] = contingency_fraction

    # Convert total amount to exact integer cents
    total_cents = int((total_amount * CENTS_FACTOR).to_integral_value())

    # Largest-remainder allocation in exact integer cents
    floored_cents: dict[str, int] = {}
    remainders: list[tuple[Fraction, int, str]] = []

    names_list = list(exact_shares.keys())
    for idx, name in enumerate(names_list):
        exact_item_cents = Fraction(total_cents) * exact_shares[name]
        base_cents = int(exact_item_cents)
        frac = exact_item_cents - Fraction(base_cents)
        floored_cents[name] = base_cents
        remainders.append((frac, -idx, name))

    allocated_sum = sum(floored_cents.values())
    shortfall = total_cents - allocated_sum
    remainders.sort(reverse=True)

    for i in range(shortfall):
        _, _, category_name = remainders[i % len(remainders)]
        floored_cents[category_name] += 1

    lines: list[BudgetLine] = []
    cfg_map = {c.name: c for c in configs}

    for name in raw_weights:
        cents = floored_cents[name]
        amount = (Decimal(cents) / CENTS_FACTOR).quantize(ONE_CENT)
        pct = ((Decimal(cents) / Decimal(total_cents)) * Decimal("100.00")).quantize(
            ONE_PERCENT, rounding=ROUND_HALF_UP
        )
        cfg = cfg_map[name]
        lines.append(
            BudgetLine(
                category=name,
                percent=pct,
                amount=amount,
                rationale=cfg.rationale,
                saving_tip=cfg.saving_tip,
            )
        )

    contingency_cents = floored_cents["Contingency Fund"]
    contingency_amt = (Decimal(contingency_cents) / CENTS_FACTOR).quantize(ONE_CENT)
    contingency_pct = (
        (Decimal(contingency_cents) / Decimal(total_cents)) * Decimal("100.00")
    ).quantize(ONE_PERCENT, rounding=ROUND_HALF_UP)
    lines.append(
        BudgetLine(
            category="Contingency Fund",
            percent=contingency_pct,
            amount=contingency_amt,
            rationale="Buffer reserved for unexpected expenses and fee variations.",
            saving_tip="Do not allocate this buffer until 2 weeks before the event.",
        )
    )

    cost_per_guest = (total_amount / Decimal(guest_count)).quantize(
        ONE_CENT, rounding=ROUND_HALF_UP
    )

    return BudgetPlan(
        total_amount=total_amount.quantize(ONE_CENT),
        currency=currency.upper(),
        guest_count=guest_count,
        cost_per_guest=cost_per_guest,
        lines=lines,
        contingency_amount=contingency_amt,
    )
