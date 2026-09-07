from app.core.config import get_settings
from app.helpers.tracking import build_tracking_url
from app.models.order import Order
from app.services.email_service import EmailService


def shop_order_url(order: Order) -> str:
    return f"{get_settings().SHOP_APP_URL.rstrip('/')}/shop/orders/{order.id}"


def send_order_email(order: Order, *, event: str, emails: EmailService | None = None) -> None:
    user = order.user
    if user is None or not user.email:
        return

    settings = get_settings()
    action_url = shop_order_url(order)
    extra = ""
    if event == "paid":
        subject = f"Payment received for order #{order.order_number}"
        headline = "Payment received"
        intro = f"Thanks — we received your payment and {settings.PROJECT_NAME} will start packing your order."
    elif event == "shipped":
        subject = f"Order #{order.order_number} is on the way"
        headline = "Your order has shipped"
        intro = "Your parcel is on its way. Use the tracking details below if they were provided."
        parts: list[str] = []
        if order.shipping_carrier:
            parts.append(f"Carrier: {order.shipping_carrier}")
        if order.tracking_number:
            parts.append(f"Tracking: {order.tracking_number}")
        tracking_url = build_tracking_url(order.shipping_carrier, order.tracking_number)
        if tracking_url:
            parts.append(f"Track: {tracking_url}")
        extra = "\n".join(parts)
    elif event == "cancelled":
        subject = f"Order #{order.order_number} was cancelled"
        headline = "Order cancelled"
        intro = "Your order was cancelled."
        if order.amount_refunded and order.amount_refunded > 0:
            extra = (
                f"A refund of {order.amount_refunded} has been issued, including the Stripe fee. "
                "The store covers processing on cancellations before ship."
            )
    elif event == "return_approved":
        subject = f"Return approved for order #{order.order_number}"
        headline = "Return approved"
        intro = "Your return was approved. Merchandise has been refunded; the Stripe fee is not returned."
        if order.amount_refunded and order.amount_refunded > 0:
            extra = f"Refunded amount: {order.amount_refunded}."
    elif event == "return_rejected":
        subject = f"Return update for order #{order.order_number}"
        headline = "Return request not approved"
        intro = "We were not able to approve this return."
        if order.return_admin_note:
            extra = order.return_admin_note
    else:
        return

    (emails or EmailService()).send_order_notice(
        to_email=user.email,
        subject=subject,
        headline=headline,
        intro=intro,
        order_number=order.order_number,
        extra=extra,
        action_url=action_url,
    )
