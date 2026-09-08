from tests.conftest import admin_headers, create_category, create_product
from tests.test_staff_roles import staff_headers
from app.models.user import UserRole


def test_lowering_stock_emails_manager_and_fulfillment(client, api_prefix, monkeypatch):
    calls: list[dict] = []

    def fake_send(self, *, to_email, subject, headline, intro):
        calls.append({"to_email": to_email, "subject": subject, "headline": headline})

    monkeypatch.setattr("app.services.email_service.EmailService.send_staff_notice", fake_send)

    admin = admin_headers(client, api_prefix)
    staff_headers(client, api_prefix, UserRole.MANAGER)
    staff_headers(client, api_prefix, UserRole.FULFILLMENT)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="9.00", stock=40, name="Restock-me")

    product = client.get(f"{api_prefix}/admin/products/{product_id}", headers=admin).json()["product"]
    updated = client.put(
        f"{api_prefix}/admin/products/{product_id}",
        json={
            "name": product["name"],
            "description": product["description"],
            "price": product["price"],
            "stock": 2,
            "categoryId": product["categoryId"],
        },
        headers=admin,
    )
    assert updated.status_code == 200, updated.text
    assert len(calls) >= 2
    assert all(item["subject"].startswith("Low stock") for item in calls)

    calls.clear()
    again = client.put(
        f"{api_prefix}/admin/products/{product_id}",
        json={
            "name": product["name"],
            "description": product["description"],
            "price": product["price"],
            "stock": 1,
            "categoryId": product["categoryId"],
        },
        headers=admin,
    )
    assert again.status_code == 200, again.text
    assert len(calls) == 0

    fulfillment = staff_headers(client, api_prefix, UserRole.FULFILLMENT)
    listed = client.get(f"{api_prefix}/admin/dashboard/low-stock", headers=fulfillment)
    assert listed.status_code == 200, listed.text
    assert product_id in [item["id"] for item in listed.json()["data"]]
