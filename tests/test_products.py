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
        f"{api_prefix}/admin/products",
        json={
            "name": f"iPhone-{uuid4().hex[:6]}",
            "description": "Apple smartphone",
            "price": "999.99",
            "stock": 25,
            "categoryId": category_id,
        },
        headers=admin,
    )
    assert create.status_code == 201
    product = create.json()["product"]
    product_id = product["id"]
    assert product["stock"] == 25

    listing = client.get(f"{api_prefix}/products", headers=user_headers)
    assert listing.status_code == 200
    assert any(item["id"] == product_id for item in listing.json()["data"])

    detail = client.get(f"{api_prefix}/products/{product_id}", headers=user_headers)
    assert detail.status_code == 200

    update = client.put(
        f"{api_prefix}/admin/products/{product_id}",
        json={
            "name": f"iPhone-Pro-{uuid4().hex[:6]}",
            "description": "Pro model",
            "price": "1199.99",
            "stock": 10,
            "categoryId": category_id,
        },
        headers=admin,
    )
    assert update.status_code == 200
    assert update.json()["product"]["stock"] == 10

    delete = client.delete(f"{api_prefix}/admin/products/{product_id}", headers=admin)
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
        f"{api_prefix}/admin/products",
        json={
            "name": laptop_name,
            "description": "Work laptop",
            "price": "1500.00",
            "stock": 5,
            "categoryId": electronics_id,
        },
        headers=admin,
    )
    client.post(
        f"{api_prefix}/admin/products",
        json={
            "name": book_name,
            "description": "Programming book",
            "price": "45.00",
            "stock": 20,
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
        f"{api_prefix}/admin/products",
        json={
            "name": f"Ghost-{uuid4().hex[:6]}",
            "price": "10.00",
            "stock": 1,
            "categoryId": "550e8400-e29b-41d4-a716-446655440000",
        },
        headers=admin,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_dashboard_product_fields_filters_and_related(client, api_prefix, signup_payload):
    user = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    other_category = create_category(client, api_prefix, admin)

    create = client.post(
        f"{api_prefix}/admin/products",
        json={
            "name": f"SaleTee-{uuid4().hex[:6]}",
            "description": "Sale item",
            "brand": "Nexus",
            "sku": f"TEE-{uuid4().hex[:6]}",
            "price": "49.99",
            "priceSale": "39.99",
            "colors": ["Black", "White"],
            "status": "sale",
            "stock": 0,
            "categoryId": category_id,
            "variants": [
                {"name": "Black / M", "color": "Black", "size": "M", "stock": 4},
                {"name": "White / L", "color": "White", "size": "L", "stock": 6},
            ],
        },
        headers=admin,
    )
    assert create.status_code == 201
    product = create.json()["product"]
    product_id = product["id"]
    assert product["priceSale"] == "39.99"
    assert product["colors"] == ["Black", "White"]
    assert product["status"] == "sale"
    assert product["brand"] == "Nexus"
    assert product["hasVariants"] is True
    assert product["stock"] == 10

    sibling = create_product(client, api_prefix, admin, category_id, stock=3)
    create_product(client, api_prefix, admin, other_category, stock=1)

    update = client.put(
        f"{api_prefix}/admin/products/{product_id}",
        json={
            "name": product["name"],
            "description": "Updated sale item",
            "brand": "Nexus",
            "sku": product["sku"],
            "price": "49.99",
            "priceSale": "34.99",
            "colors": ["Black"],
            "status": "sale",
            "stock": 0,
            "categoryId": category_id,
            "variants": [
                {
                    "id": product["variants"][0]["id"],
                    "name": "Black / M",
                    "color": "Black",
                    "size": "M",
                    "stock": 8,
                },
                {
                    "name": "Black / L",
                    "color": "Black",
                    "size": "L",
                    "stock": 2,
                },
            ],
        },
        headers=admin,
    )
    assert update.status_code == 200
    updated = update.json()["product"]
    assert updated["priceSale"] == "34.99"
    assert updated["colors"] == ["Black"]
    assert updated["stock"] == 10
    assert len(updated["variants"]) == 2

    filtered = client.get(
        f"{api_prefix}/products",
        params={"status": "sale", "onSale": True, "minPrice": "40", "sort": "priceAsc"},
        headers=user,
    )
    assert filtered.status_code == 200
    assert any(item["id"] == product_id for item in filtered.json()["data"])

    related = client.get(
        f"{api_prefix}/products/related/{product_id}",
        headers=user,
    )
    assert related.status_code == 200
    related_ids = {item["id"] for item in related.json()["data"]}
    assert sibling in related_ids
    assert product_id not in related_ids
