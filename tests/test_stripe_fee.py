from decimal import Decimal

from app.helpers.stripe_fee import (
    breakdown_with_stripe_fee,
    calculate_stripe_charge_amount,
    calculate_stripe_processing_fee,
)


def test_calculate_stripe_processing_fee_covers_stripe_cut():
    # Customer pays fee so merchant nets the subtotal after 2.9% + $0.30.
    fee = calculate_stripe_processing_fee(Decimal("100.00"))
    total = calculate_stripe_charge_amount(Decimal("100.00"))

    assert fee == Decimal("3.30")
    assert total == Decimal("103.30")

    # Stripe takes ~2.9% of charge + $0.30 ≈ fee; merchant ≈ subtotal.
    stripe_cut = (total * Decimal("0.029") + Decimal("0.30")).quantize(Decimal("0.01"))
    net = total - stripe_cut
    assert net == Decimal("100.00")


def test_breakdown_with_stripe_fee():
    breakdown = breakdown_with_stripe_fee(Decimal("44.00"))
    assert breakdown.subtotal == Decimal("44.00")
    assert breakdown.fee == Decimal("1.62")
    assert breakdown.total == Decimal("45.62")


def test_zero_amount_has_no_fee():
    assert calculate_stripe_processing_fee(Decimal("0")) == Decimal("0.00")
    assert calculate_stripe_charge_amount(Decimal("0")) == Decimal("0.00")
