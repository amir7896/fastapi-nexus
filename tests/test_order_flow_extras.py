from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import UUID

from app.db.session import SessionLocal
from app.models.order import Order
from tests.conftest import admin_headers, login_headers
from tests.test_returns import _create_paid_order, _ship


def _backdate_shipped(order_id: str, *, days: int = 8) -> None:
    db = SessionLocal()
    try:
        order = db.get(Order, UUID(order_id))
        assert order is not None
        order.shipped_at = datetime.now(timezone.utc) - timedelta(days=days)
        db.commit()
    finally:
        db.close()


def test_ship_includes_carrier_and_tracking_url(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)

    processing = client.patch(
        f"{api_prefix}/admin/orders/{order['id']}/status",
        json={"status": "PROCESSING"},
        headers=admin,
    )
    assert processing.status_code == 200, processing.text
    shipped = client.patch(
        f"{api_prefix}/admin/orders/{order['id']}/status",
        json={"status": "SHIPPED", "trackingNumber": "1Z999", "shippingCarrier": "UPS"},
        headers=admin,
    )
    assert shipped.status_code == 200, shipped.text
    body = shipped.json()["order"]
    assert body["status"] == "SHIPPED"
    assert body["shippingCarrier"] == "UPS"
    assert body["trackingNumber"] == "1Z999"
    assert body["trackingUrl"]
    assert "ups.com" in body["trackingUrl"]
    assert body["shippedAt"]


def test_admin_can_mark_shipped_order_received(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    _ship(client, api_prefix, admin, order["id"])

    response = client.post(
        f"{api_prefix}/admin/orders/{order['id']}/received",
        headers=admin,
    )
    assert response.status_code == 200, response.text
    assert response.json()["order"]["status"] == "DELIVERED"


def test_stale_shipped_order_auto_delivers_on_get(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    _ship(client, api_prefix, admin, order["id"])
    _backdate_shipped(order["id"], days=8)

    response = client.get(f"{api_prefix}/orders/{order['id']}", headers=user_headers)
    assert response.status_code == 200, response.text
    assert response.json()["order"]["status"] == "DELIVERED"


def test_admin_can_filter_pending_returns(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    _ship(client, api_prefix, admin, order["id"])
    client.post(f"{api_prefix}/orders/{order['id']}/received", headers=user_headers)
    requested = client.post(
        f"{api_prefix}/orders/{order['id']}/return",
        json={"reason": "damaged"},
        headers=user_headers,
    )
    assert requested.status_code == 200, requested.text

    listing = client.get(
        f"{api_prefix}/admin/orders",
        params={"returnStatus": "PENDING"},
        headers=admin,
    )
    assert listing.status_code == 200, listing.text
    ids = [item["id"] for item in listing.json()["data"]]
    assert order["id"] in ids
    match = next(item for item in listing.json()["data"] if item["id"] == order["id"])
    assert match["returnStatus"] == "PENDING"


def test_reorder_adds_items_to_cart(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)

    response = client.post(f"{api_prefix}/orders/{order['id']}/reorder", headers=user_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["skipped"] == []
    assert body["cart"]["items"]
    assert body["cart"]["items"][0]["quantity"] == 2


def test_order_emails_sent_for_paid_ship_and_cancel(client, api_prefix, signup_payload, monkeypatch):
    sent: list[dict] = []
    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_order_notice",
        lambda self, **kwargs: sent.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.stripe_payment_service.stripe.Refund.create",
        lambda **kwargs: MagicMock(id="re_test_email_cancel"),
    )
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    assert any(item.get("headline") == "Payment received" for item in sent)

    cancelled = client.post(f"{api_prefix}/orders/{order['id']}/cancel", headers=user_headers)
    assert cancelled.status_code == 200, cancelled.text
    assert any(item.get("headline") == "Order cancelled" for item in sent)


def test_ship_rejects_unknown_carrier(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    client.patch(
        f"{api_prefix}/admin/orders/{order['id']}/status",
        json={"status": "PROCESSING"},
        headers=admin,
    )
    response = client.patch(
        f"{api_prefix}/admin/orders/{order['id']}/status",
        json={"status": "SHIPPED", "shippingCarrier": "Pigeon"},
        headers=admin,
    )
    assert response.status_code == 400
