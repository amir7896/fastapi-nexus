from uuid import uuid4

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from tests.conftest import auth_headers


def _login_headers(client, api_prefix, signup_payload) -> dict[str, str]:
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    token = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    ).json()["access_token"]
    return auth_headers(token)


def _create_admin_and_login(client, api_prefix) -> dict[str, str]:
    email = f"admin-{uuid4().hex}@gmail.com"
    password = "Secret123"

    db = SessionLocal()
    try:
        UserRepository(db).create(
            name="Admin",
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
        )
    finally:
        db.close()

    token = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return auth_headers(token)


def test_list_users_requires_auth(client, api_prefix):
    response = client.get(f"{api_prefix}/users")
    assert response.status_code == 401


def test_list_users_with_search_and_pagination(client, api_prefix, signup_payload):
    headers = _login_headers(client, api_prefix, signup_payload)

    for index in range(1, 6):
        client.post(
            f"{api_prefix}/auth/signup",
            json={
                "name": f"User {index}",
                "email": f"user-{index}-{uuid4().hex}@gmail.com",
                "password": "Secret123",
                "age": 20 + index,
            },
        )

    listing = client.get(
        f"{api_prefix}/users",
        params={"page": 1, "limit": 3},
        headers=headers,
    )
    assert listing.status_code == 200
    body = listing.json()
    assert len(body["data"]) == 3
    assert body["meta"]["page"] == 1
    assert body["meta"]["limit"] == 3
    assert body["meta"]["total"] >= 6
    assert "password" not in body["data"][0]
    assert "password_hash" not in body["data"][0]

    search = client.get(
        f"{api_prefix}/users",
        params={"search": signup_payload["name"]},
        headers=headers,
    )
    assert search.status_code == 200
    assert search.json()["meta"]["total"] >= 1
    assert any(
        item["email"] == signup_payload["email"] for item in search.json()["data"]
    )


def test_get_update_delete_user_flow(client, api_prefix, signup_payload):
    user_headers = _login_headers(client, api_prefix, signup_payload)
    me = client.get(f"{api_prefix}/auth/me", headers=user_headers).json()
    user_id = me["id"]

    detail = client.get(f"{api_prefix}/users/{user_id}", headers=user_headers)
    assert detail.status_code == 200
    assert detail.json()["user"]["email"] == signup_payload["email"]

    update = client.put(
        f"{api_prefix}/users/{user_id}",
        json={"name": "Updated Amir", "age": 30},
        headers=user_headers,
    )
    assert update.status_code == 200
    assert update.json()["user"]["name"] == "Updated Amir"
    assert update.json()["user"]["age"] == 30

    other = {
        "name": "Other",
        "email": f"other-{uuid4().hex}@gmail.com",
        "password": "Secret123",
        "age": 22,
    }
    client.post(f"{api_prefix}/auth/signup", json=other)
    other_id = client.post(
        f"{api_prefix}/auth/login",
        json={"email": other["email"], "password": other["password"]},
    ).json()["user"]["id"]

    forbidden_update = client.put(
        f"{api_prefix}/users/{other_id}",
        json={"name": "Hacked", "age": 99},
        headers=user_headers,
    )
    assert forbidden_update.status_code == 403

    forbidden_delete = client.delete(
        f"{api_prefix}/users/{other_id}",
        headers=user_headers,
    )
    assert forbidden_delete.status_code == 403

    admin_headers = _create_admin_and_login(client, api_prefix)
    delete = client.delete(f"{api_prefix}/users/{other_id}", headers=admin_headers)
    assert delete.status_code == 200
    assert delete.json()["user"]["id"] == other_id

    missing = client.get(f"{api_prefix}/users/{other_id}", headers=admin_headers)
    assert missing.status_code == 404
