from tests.conftest import admin_headers, create_category, create_product


def test_admin_low_stock_lists_products_at_or_below_threshold(client, api_prefix):
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    low_id = create_product(client, api_prefix, admin, category_id, price="9.00", stock=2, name="Low-stock-item")
    create_product(client, api_prefix, admin, category_id, price="9.00", stock=40, name="Plenty-item")

    response = client.get(f"{api_prefix}/admin/dashboard/low-stock", headers=admin)
    assert response.status_code == 200, response.text
    ids = [item["id"] for item in response.json()["data"]]
    assert low_id in ids
    match = next(item for item in response.json()["data"] if item["id"] == low_id)
    assert match["stock"] == 2
    assert match["isOutOfStock"] is False
