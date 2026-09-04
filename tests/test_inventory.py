from tests.conftest import admin_headers, create_category, create_product, login_headers, order_payload


def test_order_rejects_insufficient_stock(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(
        client,
        api_prefix,
        admin,
        category_id,
        price="20.00",
        stock=2,
    )

    response = client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id, quantity=5),
        headers=user_headers,
    )

    assert response.status_code == 400
    assert "insufficient stock" in response.json()["detail"].lower()

    product = client.get(
        f"{api_prefix}/products/{product_id}",
        headers=user_headers,
    ).json()["product"]
    assert product["stock"] == 2


def test_order_decrements_stock(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(
        client,
        api_prefix,
        admin,
        category_id,
        price="15.00",
        stock=10,
    )

    response = client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id, quantity=3),
        headers=user_headers,
    )
    assert response.status_code == 201

    product = client.get(
        f"{api_prefix}/products/{product_id}",
        headers=user_headers,
    ).json()["product"]
    assert product["stock"] == 7


def test_cart_rejects_quantity_above_stock(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(
        client,
        api_prefix,
        admin,
        category_id,
        stock=1,
    )

    response = client.post(
        f"{api_prefix}/cart/items",
        json={"productId": product_id, "quantity": 3},
        headers=user_headers,
    )

    assert response.status_code == 400
    assert "insufficient stock" in response.json()["detail"].lower()


def test_cart_checkout_decrements_stock(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(
        client,
        api_prefix,
        admin,
        category_id,
        price="30.00",
        stock=8,
    )

    add = client.post(
        f"{api_prefix}/cart/items",
        json={"productId": product_id, "quantity": 2},
        headers=user_headers,
    )
    assert add.status_code == 201

    checkout = client.post(
        f"{api_prefix}/cart/checkout",
        json={"paymentMethodId": "pm_test_123"},
        headers=user_headers,
    )
    assert checkout.status_code == 201

    product = client.get(
        f"{api_prefix}/products/{product_id}",
        headers=user_headers,
    ).json()["product"]
    assert product["stock"] == 6
