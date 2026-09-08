from datetime import datetime, timezone

from tests.conftest import admin_headers, create_category, create_product, login_headers, order_payload
from tests.test_staff_roles import staff_headers
from app.models.user import UserRole


def _shipping():
    return {
        "name": "Amir Shahzad",
        "phoneCountryCode": "+92",
        "phone": "3001234567",
        "address": "Street 1",
        "city": "Lahore",
        "state": "Punjab",
        "country": "Pakistan",
    }


def test_finance_report_includes_paid_order(client, api_prefix, signup_payload):
    admin = admin_headers(client, api_prefix)
    user = login_headers(client, api_prefix, signup_payload)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="40.00", stock=20)
    created = client.post(
        f"{api_prefix}/orders",
        json={**order_payload(product_id), "shipping": _shipping()},
        headers=user,
    )
    assert created.status_code == 201, created.text
    order = created.json()["order"]

    today = datetime.now(timezone.utc).date().isoformat()
    finance = staff_headers(client, api_prefix, UserRole.FINANCE)
    response = client.get(
        f"{api_prefix}/admin/reports/summary",
        params={"from": today, "to": today},
        headers=finance,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["orderCount"] >= 1
    assert float(data["sales"]) >= float(order["total"])
    assert float(data["stripeFees"]) >= 0
    assert data["days"]


def test_support_cannot_view_finance_reports(client, api_prefix):
    headers = staff_headers(client, api_prefix, UserRole.SUPPORT)
    response = client.get(f"{api_prefix}/admin/reports/summary", headers=headers)
    assert response.status_code == 403
