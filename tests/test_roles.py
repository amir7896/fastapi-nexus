from uuid import uuid4

from tests.conftest import admin_headers, create_category, create_product, login_headers


def test_user_cannot_create_category(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)

    response = client.post(
        f"{api_prefix}/categories",
        json={"name": "Electronics"},
        headers=user_headers,
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_user_cannot_create_product(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)

    response = client.post(
        f"{api_prefix}/products",
        json={
            "name": "Phone",
            "price": "99.99",
            "categoryId": category_id,
        },
        headers=user_headers,
    )
    assert response.status_code == 403


def test_user_can_read_categories_and_products(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin, name=f"Read-{uuid4().hex[:6]}")
    product_id = create_product(client, api_prefix, admin, category_id)

    categories = client.get(f"{api_prefix}/categories", headers=user_headers)
    products = client.get(f"{api_prefix}/products", headers=user_headers)
    category = client.get(f"{api_prefix}/categories/{category_id}", headers=user_headers)
    product = client.get(f"{api_prefix}/products/{product_id}", headers=user_headers)

    assert categories.status_code == 200
    assert products.status_code == 200
    assert category.status_code == 200
    assert product.status_code == 200
