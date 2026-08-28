from uuid import uuid4

from tests.conftest import admin_headers, create_category, create_product, login_headers


def test_products_require_auth(client, api_prefix):
    response = client.get(f"{api_prefix}/products")
    assert response.status_code == 401


def test_product_crud_flow(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)

    create = client.post(
        f"{api_prefix}/products",
        json={
            "name": f"iPhone-{uuid4().hex[:6]}",
            "description": "Apple smartphone",
            "price": "999.99",
            "categoryId": category_id,
        },
        headers=admin,
    )
    assert create.status_code == 201
    product = create.json()["product"]
    product_id = product["id"]

    listing = client.get(f"{api_prefix}/products", headers=user_headers)
    assert listing.status_code == 200
    assert any(item["id"] == product_id for item in listing.json()["data"])

    detail = client.get(f"{api_prefix}/products/{product_id}", headers=user_headers)
    assert detail.status_code == 200

    update = client.put(
        f"{api_prefix}/products/{product_id}",
        json={
            "name": f"iPhone-Pro-{uuid4().hex[:6]}",
            "description": "Pro model",
            "price": "1199.99",
            "categoryId": category_id,
        },
        headers=admin,
    )
    assert update.status_code == 200

    delete = client.delete(f"{api_prefix}/products/{product_id}", headers=admin)
    assert delete.status_code == 200

    after_delete = client.get(f"{api_prefix}/products/{product_id}", headers=user_headers)
    assert after_delete.status_code == 404


def test_product_search_and_category_filter(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    electronics_id = create_category(client, api_prefix, admin)
    books_id = create_category(client, api_prefix, admin)

    laptop_name = f"Laptop-{uuid4().hex[:6]}"
    book_name = f"PythonGuide-{uuid4().hex[:6]}"

    client.post(
        f"{api_prefix}/products",
        json={
            "name": laptop_name,
            "description": "Work laptop",
            "price": "1500.00",
            "categoryId": electronics_id,
        },
        headers=admin,
    )
    client.post(
        f"{api_prefix}/products",
        json={
            "name": book_name,
            "description": "Programming book",
            "price": "45.00",
            "categoryId": books_id,
        },
        headers=admin,
    )

    search = client.get(
        f"{api_prefix}/products",
        params={"search": laptop_name[:10]},
        headers=user_headers,
    )
    assert search.status_code == 200
    assert search.json()["meta"]["total"] >= 1

    filtered = client.get(
        f"{api_prefix}/products",
        params={"categoryId": books_id},
        headers=user_headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["meta"]["total"] == 1


def test_create_product_rejects_missing_category(client, api_prefix, signup_payload):
    admin = admin_headers(client, api_prefix)

    response = client.post(
        f"{api_prefix}/products",
        json={
            "name": f"Ghost-{uuid4().hex[:6]}",
            "price": "10.00",
            "categoryId": "550e8400-e29b-41d4-a716-446655440000",
        },
        headers=admin,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"
