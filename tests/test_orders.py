from uuid import uuid4

from tests.conftest import admin_headers, create_category, create_product, login_headers, order_payload


def test_orders_require_auth(client, api_prefix):
    response = client.get(f"{api_prefix}/orders")
    assert response.status_code == 401


def test_create_and_get_order(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="50.00")

    create = client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id, quantity=2),
        headers=user_headers,
    )
    assert create.status_code == 201
    order = create.json()["order"]
    assert order["status"] == "PAID"
    assert order["subtotal"] == "100.00"
    assert order["stripeFee"] == "3.30"
    assert order["total"] == "103.30"
    assert order["paymentMethodId"] == "pm_test_123"
    assert order["paymentIntentId"] == "pi_test_123"

    order_id = order["id"]
    detail = client.get(f"{api_prefix}/orders/{order_id}", headers=user_headers)
    assert detail.status_code == 200


def test_list_orders_shows_only_own_orders(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id),
        headers=user_headers,
    )

    other_payload = {
        "name": "Other",
        "email": f"other-{uuid4().hex}@gmail.com",
        "password": "Secret123",
        "age": 22,
    }
    other_headers = login_headers(client, api_prefix, other_payload)
    listing = client.get(f"{api_prefix}/orders", headers=other_headers)
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] == 0


def test_admin_updates_order_status(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    order_id = client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id),
        headers=user_headers,
    ).json()["order"]["id"]

    forbidden = client.patch(
        f"{api_prefix}/admin/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=user_headers,
    )
    assert forbidden.status_code == 403

    cancelled = client.patch(
        f"{api_prefix}/admin/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=admin,
    )
    assert cancelled.status_code == 200


def test_create_order_rejects_missing_product(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)

    response = client.post(
        f"{api_prefix}/orders",
        json={
            "items": [
                {
                    "productId": "550e8400-e29b-41d4-a716-446655440000",
                    "quantity": 1,
                }
            ],
            "paymentMethodId": "pm_test_123",
        },
        headers=user_headers,
    )
    assert response.status_code == 404


def test_create_order_requires_payment_method_id(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    response = client.post(
        f"{api_prefix}/orders",
        json={"items": [{"productId": product_id, "quantity": 1}]},
        headers=user_headers,
    )
    assert response.status_code == 422
