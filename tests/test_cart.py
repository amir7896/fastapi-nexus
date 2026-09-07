from uuid import uuid4

from tests.conftest import admin_headers, create_category, create_product, login_headers


def test_cart_add_list_update_remove_and_checkout(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="50.00")

    empty = client.get(f"{api_prefix}/cart", headers=user_headers)
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    add = client.post(
        f"{api_prefix}/cart/items",
        json={"productId": product_id, "quantity": 2},
        headers=user_headers,
    )
    assert add.status_code == 201
    assert add.json()["total"] == "100.00"
    assert "imageUrl" in add.json()["items"][0]

    update = client.put(
        f"{api_prefix}/cart/items/{product_id}",
        json={"quantity": 3},
        headers=user_headers,
    )
    assert update.status_code == 200
    assert update.json()["total"] == "150.00"

    checkout = client.post(
        f"{api_prefix}/cart/checkout",
        json={"paymentMethodId": "pm_test_123"},
        headers=user_headers,
    )
    assert checkout.status_code == 201
    assert checkout.json()["order"]["status"] == "PAID"
    assert checkout.json()["order"]["subtotal"] == "150.00"
    assert checkout.json()["order"]["stripeFee"] == "4.79"
    assert checkout.json()["order"]["total"] == "154.79"
    assert checkout.json()["order"]["paymentMethodId"] == "pm_test_123"

    after_checkout = client.get(f"{api_prefix}/cart", headers=user_headers)
    assert after_checkout.json()["items"] == []


def test_cart_checkout_requires_items(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)

    response = client.post(
        f"{api_prefix}/cart/checkout",
        json={"paymentMethodId": "pm_test_123"},
        headers=user_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"


def test_cart_rejects_missing_product(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)

    response = client.post(
        f"{api_prefix}/cart/items",
        json={
            "productId": "550e8400-e29b-41d4-a716-446655440000",
            "quantity": 1,
        },
        headers=user_headers,
    )
    assert response.status_code == 404


def test_cart_clear(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    client.post(
        f"{api_prefix}/cart/items",
        json={"productId": product_id, "quantity": 1},
        headers=user_headers,
    )

    cleared = client.delete(f"{api_prefix}/cart", headers=user_headers)
    assert cleared.status_code == 200
    assert cleared.json()["items"] == []
