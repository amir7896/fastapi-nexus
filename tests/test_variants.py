from uuid import uuid4

from tests.conftest import admin_headers, create_category, create_product, login_headers, order_payload


def _create_variant(client, api_prefix, headers, product_id, *, name="Black / M", stock=5, price=None):
    body = {
        "name": name,
        "sku": "SKU-BLK-M",
        "color": "Black",
        "size": "M",
        "stock": stock,
    }
    if price is not None:
        body["price"] = price
    response = client.post(
        f"{api_prefix}/admin/products/{product_id}/variants",
        json=body,
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["variant"]


def test_create_product_with_variants_in_payload(client, api_prefix, signup_payload):
    user = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)

    response = client.post(
        f"{api_prefix}/admin/products",
        json={
            "name": f"Tee-{uuid4().hex[:6]}",
            "description": "Cotton t-shirt",
            "price": "29.99",
            "categoryId": category_id,
            "variants": [
                {
                    "name": "Black / M",
                    "color": "Black",
                    "size": "M",
                    "stock": 3,
                },
                {
                    "name": "White / L",
                    "color": "White",
                    "size": "L",
                    "price": "32.99",
                    "stock": 7,
                },
            ],
        },
        headers=admin,
    )

    assert response.status_code == 201
    product = response.json()["product"]
    assert product["stock"] == 10
    assert len(product["variants"]) == 2
    colors = {v["color"] for v in product["variants"]}
    assert colors == {"Black", "White"}
    priced = next(v for v in product["variants"] if v["color"] == "White")
    assert priced["price"] == "32.99"

    detail = client.get(f"{api_prefix}/products/{product['id']}", headers=user)
    assert detail.status_code == 200
    assert len(detail.json()["product"]["variants"]) == 2


def test_variant_crud_and_product_stock_sum(client, api_prefix, signup_payload):
    user = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, stock=0)

    v1 = _create_variant(client, api_prefix, admin, product_id, name="Black / M", stock=3)
    v2 = _create_variant(client, api_prefix, admin, product_id, name="White / L", stock=7)

    detail = client.get(f"{api_prefix}/products/{product_id}", headers=user)
    assert detail.status_code == 200
    product = detail.json()["product"]
    assert product["stock"] == 10
    assert len(product["variants"]) == 2

    update = client.put(
        f"{api_prefix}/admin/products/{product_id}/variants/{v1['id']}",
        json={
            "name": "Black / M",
            "color": "Black",
            "size": "M",
            "stock": 4,
            "price": "1099.99",
        },
        headers=admin,
    )
    assert update.status_code == 200
    assert update.json()["variant"]["stock"] == 4

    detail = client.get(f"{api_prefix}/products/{product_id}", headers=user)
    assert detail.json()["product"]["stock"] == 11

    delete = client.delete(
        f"{api_prefix}/admin/products/{product_id}/variants/{v2['id']}",
        headers=admin,
    )
    assert delete.status_code == 200
    detail = client.get(f"{api_prefix}/products/{product_id}", headers=user)
    assert detail.json()["product"]["stock"] == 4
    assert len(detail.json()["product"]["variants"]) == 1


def test_order_requires_variant_when_product_has_variants(client, api_prefix, signup_payload):
    user = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="50.00", stock=0)
    _create_variant(client, api_prefix, admin, product_id, stock=2)

    response = client.post(
        f"{api_prefix}/orders",
        json=order_payload(product_id, quantity=1),
        headers=user,
    )
    assert response.status_code == 400
    assert "variantid is required" in response.json()["detail"].lower()


def test_order_with_variant_decrements_variant_stock(client, api_prefix, signup_payload):
    user = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="40.00", stock=0)
    variant = _create_variant(
        client,
        api_prefix,
        admin,
        product_id,
        stock=5,
        price="45.00",
    )

    response = client.post(
        f"{api_prefix}/orders",
        json={
            "items": [
                {
                    "productId": product_id,
                    "variantId": variant["id"],
                    "quantity": 2,
                }
            ],
            "paymentMethodId": "pm_test_123",
        },
        headers=user,
    )
    assert response.status_code == 201
    order = response.json()["order"]
    assert order["subtotal"] == "90.00"
    assert order["stripeFee"] == "3.00"
    assert order["total"] == "93.00"
    assert order["items"][0]["variantId"] == variant["id"]
    assert "Black / M" in order["items"][0]["productName"]

    product = client.get(f"{api_prefix}/products/{product_id}", headers=user).json()["product"]
    assert product["stock"] == 3
    assert product["variants"][0]["stock"] == 3


def test_cart_variant_flow(client, api_prefix, signup_payload):
    user = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="20.00", stock=0)
    variant = _create_variant(client, api_prefix, admin, product_id, stock=4, price="22.00")

    missing = client.post(
        f"{api_prefix}/cart/items",
        json={"productId": product_id, "quantity": 1},
        headers=user,
    )
    assert missing.status_code == 400

    add = client.post(
        f"{api_prefix}/cart/items",
        json={"productId": product_id, "variantId": variant["id"], "quantity": 2},
        headers=user,
    )
    assert add.status_code == 201
    assert add.json()["total"] == "44.00"
    assert add.json()["items"][0]["variantId"] == variant["id"]

    checkout = client.post(
        f"{api_prefix}/cart/checkout",
        json={"paymentMethodId": "pm_test_123"},
        headers=user,
    )
    assert checkout.status_code == 201
    assert checkout.json()["order"]["subtotal"] == "44.00"
    assert checkout.json()["order"]["stripeFee"] == "1.62"
    assert checkout.json()["order"]["total"] == "45.62"

    product = client.get(f"{api_prefix}/products/{product_id}", headers=user).json()["product"]
    assert product["variants"][0]["stock"] == 2
