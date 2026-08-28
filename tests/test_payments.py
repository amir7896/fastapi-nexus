from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import admin_headers, create_category, create_product, login_headers, order_payload


def test_create_order_requires_stripe(client, api_prefix, signup_payload, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()

    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    response = client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id),
        headers=user_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Stripe is not configured"


@patch("app.services.stripe_payment_service.stripe.checkout.Session.create")
def test_create_checkout_session_for_pending_order(
    mock_create_session,
    client,
    api_prefix,
    signup_payload,
    monkeypatch,
):
    mock_create_session.return_value = MagicMock(
        id="cs_test_123",
        url="https://checkout.stripe.com/pay/cs_test_123",
    )
    monkeypatch.setattr(
        "app.services.stripe_payment_service.stripe.PaymentIntent.create",
        MagicMock(
            return_value=MagicMock(id="pi_pending", status="requires_action"),
        ),
    )

    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="25.00")

    failed_payment = client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id, quantity=2),
        headers=user_headers,
    )
    assert failed_payment.status_code == 400

    listing = client.get(f"{api_prefix}/orders", headers=user_headers)
    order_id = listing.json()["data"][0]["id"]
    assert listing.json()["data"][0]["status"] == "PENDING"

    response = client.post(
        f"{api_prefix}/orders/{order_id}/checkout",
        headers=user_headers,
    )
    assert response.status_code == 200
    assert response.json()["checkoutUrl"] == "https://checkout.stripe.com/pay/cs_test_123"


@patch("app.services.stripe_payment_service.stripe.Webhook.construct_event")
def test_stripe_webhook_marks_order_paid(
    mock_construct_event,
    client,
    api_prefix,
    signup_payload,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.services.stripe_payment_service.stripe.PaymentIntent.create",
        MagicMock(
            return_value=MagicMock(id="pi_webhook_123", status="requires_action"),
        ),
    )

    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id),
        headers=user_headers,
    )

    listing = client.get(f"{api_prefix}/orders", headers=user_headers)
    order_id = listing.json()["data"][0]["id"]

    mock_construct_event.return_value = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_webhook_123",
                "payment_method": "pm_test_123",
                "metadata": {"order_id": order_id},
            }
        },
    }

    webhook = client.post(
        f"{api_prefix}/payments/stripe/webhook",
        content=b"{}",
        headers={"stripe-signature": "test-signature"},
    )
    assert webhook.status_code == 200

    detail = client.get(f"{api_prefix}/orders/{order_id}", headers=user_headers)
    assert detail.json()["order"]["status"] == "PAID"


def test_checkout_rejects_paid_order(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    order_id = client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id),
        headers=user_headers,
    ).json()["order"]["id"]

    response = client.post(
        f"{api_prefix}/orders/{order_id}/checkout",
        headers=user_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only pending orders can be paid"
