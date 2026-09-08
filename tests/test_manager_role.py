from uuid import uuid4

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from tests.conftest import admin_headers, auth_headers


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


def manager_headers(client, api_prefix: str) -> dict[str, str]:
    email, password = _create_verified_user(name="Manager", role=UserRole.MANAGER)
    token = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return auth_headers(token)


def test_manager_can_use_staff_login(client, api_prefix):
    email, password = _create_verified_user(name="Manager", role=UserRole.MANAGER)
    response = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "MANAGER"


def test_customer_cannot_use_staff_login(client, api_prefix):
    email, password = _create_verified_user(name="Customer", role=UserRole.USER)
    response = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 403


def test_manager_can_access_catalog_but_not_users(client, api_prefix):
    headers = manager_headers(client, api_prefix)
    products = client.get(f"{api_prefix}/admin/products", headers=headers)
    assert products.status_code == 200, products.text

    users = client.get(f"{api_prefix}/admin/users", headers=headers)
    assert users.status_code == 403


def test_admin_can_promote_user_to_manager(client, api_prefix):
    admin = admin_headers(client, api_prefix)
    email, _password = _create_verified_user(name="To Promote", role=UserRole.USER)
    listed = client.get(f"{api_prefix}/admin/users?search={email}", headers=admin)
    assert listed.status_code == 200, listed.text
    user_id = next(item["id"] for item in listed.json()["data"] if item["email"] == email)

    updated = client.put(
        f"{api_prefix}/admin/users/{user_id}",
        json={"name": "To Promote", "role": "MANAGER"},
        headers=admin,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["user"]["role"] == "MANAGER"


def test_manager_sees_support_inbox(client, api_prefix, signup_payload):
    from tests.conftest import login_headers

    customer = login_headers(client, api_prefix, signup_payload)
    created = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "GENERAL", "subject": "Need help", "message": "Hi"},
        headers=customer,
    )
    assert created.status_code == 200, created.text

    manager = manager_headers(client, api_prefix)
    inbox = client.get(f"{api_prefix}/support/conversations", headers=manager)
    assert inbox.status_code == 200, inbox.text
    assert inbox.json()["meta"]["total"] >= 1

    start = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "GENERAL", "message": "Staff should not start"},
        headers=manager,
    )
    assert start.status_code == 400
