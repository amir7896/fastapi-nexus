"""Stripe card processing fee helpers.

When the customer pays the processing fee, we gross up the product subtotal so
the merchant still nets that subtotal after Stripe's cut (percent + fixed).
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

MONEY = Decimal("0.01")

# Standard US card rates (override via settings / function kwargs).
DEFAULT_STRIPE_FEE_PERCENT = Decimal("2.9")
DEFAULT_STRIPE_FEE_FIXED = Decimal("0.30")


class StripeFeeBreakdown(NamedTuple):
    subtotal: Decimal
    fee: Decimal
    total: Decimal


def round_money(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(MONEY, rounding=ROUND_HALF_UP)


def calculate_stripe_processing_fee(
    amount: Decimal,
    *,
    percent: Decimal = DEFAULT_STRIPE_FEE_PERCENT,
    fixed: Decimal = DEFAULT_STRIPE_FEE_FIXED,
) -> Decimal:
    """Return the fee to add so the customer covers Stripe processing.

    Solves for charge ``C`` where Stripe takes ``C * rate + fixed`` and the
    merchant nets ``amount``:

        C = (amount + fixed) / (1 - rate)
        fee = C - amount
    """
    subtotal = round_money(amount)
    if subtotal <= 0:
        return Decimal("0.00")

    rate = Decimal(percent) / Decimal("100")
    if rate < 0 or rate >= 1:
        raise ValueError("Stripe fee percent must be in [0, 100)")
    fixed_fee = round_money(fixed)
    if fixed_fee < 0:
        raise ValueError("Stripe fixed fee cannot be negative")

    charge = (subtotal + fixed_fee) / (Decimal("1") - rate)
    return round_money(charge - subtotal)


def calculate_stripe_charge_amount(
    amount: Decimal,
    *,
    percent: Decimal = DEFAULT_STRIPE_FEE_PERCENT,
    fixed: Decimal = DEFAULT_STRIPE_FEE_FIXED,
) -> Decimal:
    """Product subtotal plus Stripe processing fee (amount charged to card)."""
    fee = calculate_stripe_processing_fee(amount, percent=percent, fixed=fixed)
    return round_money(Decimal(amount) + fee)


def breakdown_with_stripe_fee(
    amount: Decimal,
    *,
    percent: Decimal = DEFAULT_STRIPE_FEE_PERCENT,
    fixed: Decimal = DEFAULT_STRIPE_FEE_FIXED,
) -> StripeFeeBreakdown:
    subtotal = round_money(amount)
    fee = calculate_stripe_processing_fee(subtotal, percent=percent, fixed=fixed)
    return StripeFeeBreakdown(subtotal=subtotal, fee=fee, total=round_money(subtotal + fee))
