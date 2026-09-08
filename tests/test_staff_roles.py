from uuid import uuid4

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from tests.conftest import admin_headers, auth_headers, login_headers


def _create_verified_user(*, name: str, role: UserRole) -> tuple[str, str]:
    email = f"{role.value.lower()}-{uuid4().hex}@gmail.com"
    password = "Secret123"
    db = SessionLocal()
    try:
        UserRepository(db).create(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            email_verified=True,
        )
    finally:
        db.close()
    return email, password


def staff_headers(client, api_prefix: str, role: UserRole) -> dict[str, str]:
    email, password = _create_verified_user(name=role.value.title(), role=role)
    token = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return auth_headers(token)


def test_new_staff_roles_can_use_staff_login(client, api_prefix):
    for role in (UserRole.FINANCE, UserRole.SUPPORT, UserRole.FULFILLMENT):
        email, password = _create_verified_user(name=role.value.title(), role=role)
        response = client.post(
            f"{api_prefix}/auth/admin/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, response.text
        assert response.json()["user"]["role"] == role.value


def test_finance_can_access_orders_but_not_catalog_or_users(client, api_prefix):
    headers = staff_headers(client, api_prefix, UserRole.FINANCE)
    assert client.get(f"{api_prefix}/admin/orders", headers=headers).status_code == 200
    assert client.get(f"{api_prefix}/admin/products", headers=headers).status_code == 403
    assert client.get(f"{api_prefix}/admin/users", headers=headers).status_code == 403


def test_fulfillment_can_access_orders_but_not_catalog_or_users(client, api_prefix):
    headers = staff_headers(client, api_prefix, UserRole.FULFILLMENT)
    assert client.get(f"{api_prefix}/admin/orders", headers=headers).status_code == 200
    assert client.get(f"{api_prefix}/admin/products", headers=headers).status_code == 403
    assert client.get(f"{api_prefix}/admin/users", headers=headers).status_code == 403


def test_support_can_see_inbox_but_not_orders_or_catalog(client, api_prefix, signup_payload):
    customer = login_headers(client, api_prefix, signup_payload)
    created = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "GENERAL", "subject": "Need help", "message": "Hi"},
        headers=customer,
    )
    assert created.status_code == 200, created.text

    headers = staff_headers(client, api_prefix, UserRole.SUPPORT)
    inbox = client.get(f"{api_prefix}/support/conversations", headers=headers)
    assert inbox.status_code == 200, inbox.text
    assert inbox.json()["meta"]["total"] >= 1

    assert client.get(f"{api_prefix}/admin/orders", headers=headers).status_code == 403
    assert client.get(f"{api_prefix}/admin/products", headers=headers).status_code == 403
    assert client.get(f"{api_prefix}/admin/users", headers=headers).status_code == 403


def test_admin_can_assign_new_staff_roles(client, api_prefix):
    admin = admin_headers(client, api_prefix)
    email, _password = _create_verified_user(name="To Promote", role=UserRole.USER)
    listed = client.get(f"{api_prefix}/admin/users?search={email}", headers=admin)
    assert listed.status_code == 200, listed.text
    user_id = next(item["id"] for item in listed.json()["data"] if item["email"] == email)

    updated = client.put(
        f"{api_prefix}/admin/users/{user_id}",
        json={"name": "To Promote", "role": "FINANCE"},
        headers=admin,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["user"]["role"] == "FINANCE"
