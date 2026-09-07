from unittest.mock import MagicMock

from tests.conftest import admin_headers, create_category, create_product, login_headers, order_payload


def _shipping():
    return {
        "name": "Amir Shahzad",
        "phone": "03001234567",
        "address": "Street 1",
        "city": "Lahore",
        "country": "Pakistan",
    }


def _create_paid_order(client, api_prefix, user_headers, admin):
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="50.00")
    response = client.post(
        f"{api_prefix}/orders",
        json={**order_payload(product_id, quantity=2), "shipping": _shipping()},
        headers=user_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["order"]


def _ship(client, api_prefix, admin, order_id):
    processing = client.patch(
        f"{api_prefix}/admin/orders/{order_id}/status",
        json={"status": "PROCESSING"},
        headers=admin,
    )
    assert processing.status_code == 200, processing.text
    shipped = client.patch(
        f"{api_prefix}/admin/orders/{order_id}/status",
        json={"status": "SHIPPED", "trackingNumber": "TRK-1"},
        headers=admin,
    )
    assert shipped.status_code == 200, shipped.text


def test_admin_cannot_mark_delivered(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    _ship(client, api_prefix, admin, order["id"])

    response = client.patch(
        f"{api_prefix}/admin/orders/{order['id']}/status",
        json={"status": "DELIVERED"},
        headers=admin,
    )
    assert response.status_code == 400
    assert "customer marks" in response.json()["detail"].lower()


def test_customer_marks_received_then_return_refunds_merchandise_only(
    client, api_prefix, signup_payload, monkeypatch
):
    refunds: list[dict] = []
    monkeypatch.setattr(
        "app.services.stripe_payment_service.stripe.Refund.create",
        lambda **kwargs: refunds.append(kwargs) or MagicMock(id="re_test_return"),
    )
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    _ship(client, api_prefix, admin, order["id"])

    received = client.post(
        f"{api_prefix}/orders/{order['id']}/received",
        headers=user_headers,
    )
    assert received.status_code == 200
    assert received.json()["order"]["status"] == "DELIVERED"

    requested = client.post(
        f"{api_prefix}/orders/{order['id']}/return",
        json={"reason": "damaged", "details": "Box crushed"},
        headers=user_headers,
    )
    assert requested.status_code == 200
    assert requested.json()["order"]["returnRequest"]["status"] == "PENDING"

    approved = client.post(
        f"{api_prefix}/admin/orders/{order['id']}/return/review",
        json={"decision": "APPROVED", "adminNote": "OK"},
        headers=admin,
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()["order"]
    assert body["status"] == "RETURNED"
    assert body["amountRefunded"] == "100.00"
    assert refunds[0]["amount"] == 10000
    assert refunds[0]["payment_intent"] == "pi_test_123"


def test_cancel_refunds_full_amount_including_stripe_fee(
    client, api_prefix, signup_payload, monkeypatch
):
    refunds: list[dict] = []
    monkeypatch.setattr(
        "app.services.stripe_payment_service.stripe.Refund.create",
        lambda **kwargs: refunds.append(kwargs) or MagicMock(id="re_test_cancel"),
    )
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)

    cancelled = client.post(
        f"{api_prefix}/orders/{order['id']}/cancel",
        headers=user_headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    body = cancelled.json()["order"]
    assert body["status"] == "CANCELLED"
    assert body["amountRefunded"] == "103.30"
    assert refunds[0]["amount"] == 10330
