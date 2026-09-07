from decimal import Decimal

from app.helpers.stripe_fee import round_money
from app.models.order import Order

RETURN_WINDOW_DAYS = 14

# Cancel before the parcel is sent: store covers the Stripe surcharge.
# Approved return after delivery: customer keeps paying the surcharge.


def already_refunded(order: Order) -> Decimal:
    return round_money(order.amount_refunded or Decimal("0"))


def cancel_refund_amount(order: Order) -> Decimal:
    """Full charge minus anything already refunded."""
    return round_money(max(Decimal("0"), order.total - already_refunded(order)))


def return_refund_amount(order: Order) -> Decimal:
    """Merchandise only. Stripe processing fee is not refunded."""
    return round_money(max(Decimal("0"), order.subtotal - already_refunded(order)))


def fee_payer_for_cancel() -> str:
    return "merchant"


def fee_payer_for_return() -> str:
    return "customer"
