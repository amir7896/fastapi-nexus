from unittest.mock import MagicMock

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


def test_role_change_and_verify_appear_in_audit_log(client, api_prefix):
    admin = admin_headers(client, api_prefix)
    email, _password = _create_user()
    listed = client.get(f"{api_prefix}/admin/users?search={email}", headers=admin)
    user_id = next(item["id"] for item in listed.json()["data"] if item["email"] == email)
    user = next(item for item in listed.json()["data"] if item["id"] == user_id)

    updated = client.put(
        f"{api_prefix}/admin/users/{user_id}",
        json={"name": user["name"], "role": "SUPPORT", "emailVerified": True},
        headers=admin,
    )
    assert updated.status_code == 200, updated.text

    logs = client.get(f"{api_prefix}/admin/audit-logs", headers=admin)
    assert logs.status_code == 200, logs.text
    actions = [item["action"] for item in logs.json()["data"]]
    assert "user.role_changed" in actions
    assert "user.verified" in actions

    manager = staff_headers(client, api_prefix, UserRole.MANAGER)
    assert client.get(f"{api_prefix}/admin/audit-logs", headers=manager).status_code == 200

    finance = staff_headers(client, api_prefix, UserRole.FINANCE)
    assert client.get(f"{api_prefix}/admin/audit-logs", headers=finance).status_code == 403


def test_staff_refund_is_logged(client, api_prefix, signup_payload, monkeypatch):
    monkeypatch.setattr(
        "app.services.stripe_payment_service.stripe.Refund.create",
        MagicMock(return_value=MagicMock(id="re_test_audit")),
    )
    admin = admin_headers(client, api_prefix)
    user = login_headers(client, api_prefix, signup_payload)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="25.00", stock=10)
    created = client.post(
        f"{api_prefix}/orders",
        json={**order_payload(product_id), "shipping": _shipping()},
        headers=user,
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["order"]["id"]
    cancelled = client.patch(
        f"{api_prefix}/admin/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=admin,
    )
    assert cancelled.status_code == 200, cancelled.text

    logs = client.get(f"{api_prefix}/admin/audit-logs?action=order.refunded", headers=admin)
    assert logs.status_code == 200, logs.text
    assert logs.json()["meta"]["total"] >= 1


def _create_user() -> tuple[str, str]:
    from uuid import uuid4

    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models.user import UserRole
    from app.repositories.user_repository import UserRepository

    email = f"audit-{uuid4().hex}@gmail.com"
    password = "Secret123"
    db = SessionLocal()
    try:
        UserRepository(db).create(
            name="Audit Target",
            email=email,
            password_hash=hash_password(password),
            role=UserRole.USER,
            email_verified=False,
        )
    finally:
        db.close()
    return email, password
