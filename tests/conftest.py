from collections.abc import Iterator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import create_app
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository


@pytest.fixture(autouse=True)
def stripe_test_env(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_fake")
    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def mock_stripe_payment_intent(monkeypatch):
    mock_intent = MagicMock(id="pi_test_123", status="succeeded")
    monkeypatch.setattr(
        "app.services.stripe_payment_service.stripe.PaymentIntent.create",
        MagicMock(return_value=mock_intent),
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def api_prefix() -> str:
    return settings.API_V1_PREFIX


@pytest.fixture
def signup_payload() -> dict:
    return {
        "name": "Amir",
        "email": f"amir-{uuid4().hex}@gmail.com",
        "password": "Secret123",
        "age": 25,
    }


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def mark_email_verified(email: str) -> None:
    db = SessionLocal()
    try:
        users = UserRepository(db)
        user = users.get_by_email(email)
        assert user is not None
        users.mark_email_verified(user)
    finally:
        db.close()


def login_headers(client, api_prefix: str, signup_payload: dict) -> dict[str, str]:
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    mark_email_verified(signup_payload["email"])
    token = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    ).json()["access_token"]
    return auth_headers(token)


def admin_headers(client, api_prefix: str) -> dict[str, str]:
    email = f"admin-{uuid4().hex}@gmail.com"
    password = "Secret123"

    db = SessionLocal()
    try:
        UserRepository(db).create(
            name="Admin",
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            email_verified=True,
        )
    finally:
        db.close()

    token = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return auth_headers(token)


def create_category(
    client,
    api_prefix: str,
    headers: dict[str, str],
    name: str | None = None,
) -> str:
    response = client.post(
        f"{api_prefix}/categories",
        json={"name": name or f"Category-{uuid4().hex[:8]}"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["category"]["id"]


def create_product(
    client,
    api_prefix: str,
    headers: dict[str, str],
    category_id: str,
    *,
    price: str = "99.99",
    name: str | None = None,
) -> str:
    response = client.post(
        f"{api_prefix}/products",
        json={
            "name": name or f"Product-{uuid4().hex[:6]}",
            "description": "Test product",
            "price": price,
            "categoryId": category_id,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["product"]["id"]


def order_payload(
    product_id: str,
    *,
    quantity: int = 1,
    payment_method_id: str = "pm_test_123",
) -> dict:
    return {
        "items": [{"productId": product_id, "quantity": quantity}],
        "paymentMethodId": payment_method_id,
    }
