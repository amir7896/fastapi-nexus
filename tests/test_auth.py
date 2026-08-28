from uuid import uuid4

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository


def test_signup_creates_user_without_password(client, api_prefix, signup_payload):
    response = client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Signup successful"
    assert body["user"]["email"] == signup_payload["email"]
    assert body["user"]["role"] == "USER"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert "id" in body["user"]
    assert body["access_token"] is None


def test_signup_rejects_duplicate_email(client, api_prefix, signup_payload):
    first = client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    assert first.status_code == 201

    second = client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already exists"


def test_signup_reports_missing_field_in_plain_language(
    client, api_prefix, signup_payload
):
    signup_payload.pop("email")

    response = client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "email is required"


def test_login_returns_access_token(client, api_prefix, signup_payload):
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Login successful"
    assert body["user"]["email"] == signup_payload["email"]
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert len(body["access_token"]) > 20


def test_login_rejects_wrong_password(client, api_prefix, signup_payload):
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    response = client.post(
        f"{api_prefix}/auth/login",
        json={"email": signup_payload["email"], "password": "WrongPass123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_admin_login_rejects_regular_user(client, api_prefix, signup_payload):
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)

    response = client.post(
        f"{api_prefix}/auth/admin/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_login_returns_access_token(client, api_prefix):
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

    response = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Admin login successful"
    assert body["user"]["role"] == "ADMIN"
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_me_requires_authentication(client, api_prefix):
    response = client.get(f"{api_prefix}/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_me_returns_current_user_with_token(client, api_prefix, signup_payload):
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    login = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    )
    token = login.json()["access_token"]

    response = client.get(
        f"{api_prefix}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == signup_payload["email"]
