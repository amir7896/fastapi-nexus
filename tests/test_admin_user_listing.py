from uuid import uuid4

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from tests.conftest import admin_headers


def _create_user(*, name: str, role: UserRole = UserRole.USER, verified: bool = False) -> str:
    email = f"{role.value.lower()}-{uuid4().hex}@gmail.com"
    db = SessionLocal()
    try:
        UserRepository(db).create(
            name=name,
            email=email,
            password_hash=hash_password("Secret123"),
            role=role,
            email_verified=verified,
        )
    finally:
        db.close()
    return email


def _user_id(client, api_prefix: str, headers: dict[str, str], email: str) -> str:
    listed = client.get(f"{api_prefix}/admin/users?search={email}", headers=headers)
    assert listed.status_code == 200, listed.text
    return next(item["id"] for item in listed.json()["data"] if item["email"] == email)


def test_admin_can_verify_and_assign_role_from_update(client, api_prefix):
    admin = admin_headers(client, api_prefix)
    email = _create_user(name="Listing User", verified=False)
    user_id = _user_id(client, api_prefix, admin, email)

    updated = client.put(
        f"{api_prefix}/admin/users/{user_id}",
        json={"name": "Listing User", "role": "SUPPORT", "emailVerified": True},
        headers=admin,
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()["user"]
    assert body["role"] == "SUPPORT"
    assert body["emailVerified"] is True
