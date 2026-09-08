from uuid import uuid4

from app.models.user import UserRole
from tests.conftest import admin_headers, login_headers, mark_email_verified


def _merchant_headers(client, api_prefix: str, store_name: str) -> dict[str, str]:
    from app.core.config import get_settings

    settings = get_settings()
    previous = settings.ALLOW_PUBLIC_STORE_SIGNUP
    settings.ALLOW_PUBLIC_STORE_SIGNUP = True
    payload = {
        "name": f"{store_name} Owner",
        "email": f"{store_name.lower().replace(' ', '')}-{uuid4().hex}@gmail.com",
        "password": "Secret123",
        "age": 30,
        "storeName": store_name,
    }
    try:
        created = client.post(f"{api_prefix}/auth/signup", json=payload)
    finally:
        settings.ALLOW_PUBLIC_STORE_SIGNUP = previous
    assert created.status_code == 201, created.text
    mark_email_verified(payload["email"])
    login = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_signup_joins_default_store(client, api_prefix, signup_payload):
    response = client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    assert response.status_code == 201
    user = response.json()["user"]
    assert user["organizationSlug"] == "nexus"
    assert user["role"] == "USER"


def test_public_signup_cannot_create_a_store(client, api_prefix):
    payload = {
        "name": "Sam Seller",
        "email": f"seller-{uuid4().hex}@gmail.com",
        "password": "Secret123",
        "age": 30,
        "storeName": "Northwind",
    }
    response = client.post(f"{api_prefix}/auth/signup", json=payload)
    assert response.status_code == 201
    user = response.json()["user"]
    assert user["role"] == "USER"
    assert user["organizationSlug"] == "nexus"


def test_stores_are_isolated(client, api_prefix):
    admin = _merchant_headers(client, api_prefix, "Alpha Shop")
    category = client.post(
        f"{api_prefix}/admin/categories",
        json={"name": f"Cat-{uuid4().hex[:6]}"},
        headers=admin,
    )
    assert category.status_code == 201, category.text
    category_id = category.json()["category"]["id"]
    product = client.post(
        f"{api_prefix}/admin/products",
        json={
            "name": f"Hidden-{uuid4().hex[:6]}",
            "price": "10.00",
            "stock": 3,
            "categoryId": category_id,
        },
        headers=admin,
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["product"]["id"]

    other = _merchant_headers(client, api_prefix, "Beta Shop")
    listed = client.get(f"{api_prefix}/admin/products", headers=other)
    assert listed.status_code == 200, listed.text
    ids = [item["id"] for item in listed.json()["data"]]
    assert product_id not in ids


def test_invite_and_accept(client, api_prefix, monkeypatch):
    captured: dict = {}

    def capture_invite(self, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_staff_invite",
        capture_invite,
    )

    admin = _merchant_headers(client, api_prefix, "Invite Shop")
    invite_email = f"manager-{uuid4().hex}@gmail.com"
    created = client.post(
        f"{api_prefix}/organizations/invites",
        json={"email": invite_email, "role": UserRole.MANAGER.value},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    assert created.json()["email"] == invite_email
    token = captured["accept_url"].rstrip("/").rsplit("/", 1)[-1]
    assert token

    preview = client.get(f"{api_prefix}/organizations/invites/preview", params={"token": token})
    assert preview.status_code == 200, preview.text
    assert preview.json()["needsAccount"] is True

    accepted = client.post(
        f"{api_prefix}/organizations/invites/accept",
        json={"token": token, "name": "Pat Manager", "password": "Secret123"},
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["user"]["role"] == "MANAGER"
    assert body["access_token"]


def test_store_settings(client, api_prefix):
    headers = admin_headers(client, api_prefix)
    current = client.get(f"{api_prefix}/organizations/current", headers=headers)
    assert current.status_code == 200, current.text
    updated = client.patch(
        f"{api_prefix}/organizations/current",
        json={
            "name": "Nexus HQ",
            "currency": "usd",
            "timezone": "America/New_York",
            "taxRate": "8.5",
            "shippingFlatRate": "4.99",
            "notifyOrders": True,
            "notifyLowStock": False,
            "shopUrl": "https://shop.example.com",
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    org = updated.json()["organization"]
    assert org["name"] == "Nexus HQ"
    assert org["taxRate"] in ("8.500", "8.5", "8.50")
    assert org["notifyLowStock"] is False


def test_billing_defaults_to_free(client, api_prefix):
    headers = admin_headers(client, api_prefix)
    billing = client.get(f"{api_prefix}/organizations/billing", headers=headers)
    assert billing.status_code == 200, billing.text
    body = billing.json()
    assert body["plan"] == "free"
    ids = [item["id"] for item in body["plans"]]
    assert ids == ["free", "pro", "business"]


def test_customer_cannot_open_billing(client, api_prefix, signup_payload):
    headers = login_headers(client, api_prefix, signup_payload)
    billing = client.get(f"{api_prefix}/organizations/billing", headers=headers)
    assert billing.status_code == 403


def test_customer_cannot_create_store(client, api_prefix, signup_payload):
    headers = login_headers(client, api_prefix, signup_payload)
    response = client.post(
        f"{api_prefix}/organizations",
        json={"name": "Should Fail"},
        headers=headers,
    )
    assert response.status_code == 403


def test_upload_and_replace_store_logo(client, api_prefix, monkeypatch):
    from io import BytesIO
    from unittest.mock import MagicMock

    from PIL import Image

    from app.core.config import get_settings
    from app.helpers.image_types import StoredImage

    monkeypatch.setenv("IMAGE_STORAGE_PROVIDER", "cloudinary")
    get_settings.cache_clear()
    upload = MagicMock(
        side_effect=[
            StoredImage(
                url="https://cdn.example/logo-one.png",
                public_id="Nexus/logos/one",
                provider="cloudinary",
            ),
            StoredImage(
                url="https://cdn.example/logo-two.png",
                public_id="Nexus/logos/two",
                provider="cloudinary",
            ),
        ]
    )
    delete = MagicMock()
    monkeypatch.setattr("app.services.image_storage_service.upload_product_image", upload)
    monkeypatch.setattr("app.services.image_storage_service.delete_product_image", delete)

    def png_file(name: str = "logo.png"):
        buffer = BytesIO()
        Image.new("RGB", (2, 2), color=(32, 101, 209)).save(buffer, format="PNG")
        buffer.seek(0)
        return {"file": (name, buffer, "image/png")}

    headers = admin_headers(client, api_prefix)
    first = client.post(
        f"{api_prefix}/organizations/current/logo",
        files=png_file(),
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["organization"]["logoUrl"] == "https://cdn.example/logo-one.png"

    second = client.post(
        f"{api_prefix}/organizations/current/logo",
        files=png_file("other.png"),
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["organization"]["logoUrl"] == "https://cdn.example/logo-two.png"
    delete.assert_called_once_with("Nexus/logos/one")

    removed = client.delete(f"{api_prefix}/organizations/current/logo", headers=headers)
    assert removed.status_code == 200, removed.text
    assert removed.json()["organization"]["logoUrl"] is None
    assert delete.call_count == 2

    saved = client.patch(
        f"{api_prefix}/organizations/current",
        json={
            "name": "Nexus HQ",
            "currency": "usd",
            "timezone": "UTC",
            "taxRate": "0",
            "shippingFlatRate": "0",
            "notifyOrders": True,
            "notifyLowStock": True,
        },
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["organization"]["logoUrl"] is None
    get_settings.cache_clear()


def test_customer_cannot_upload_store_logo(client, api_prefix, signup_payload):
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(32, 101, 209)).save(buffer, format="PNG")
    buffer.seek(0)
    headers = login_headers(client, api_prefix, signup_payload)
    response = client.post(
        f"{api_prefix}/organizations/current/logo",
        files={"file": ("logo.png", buffer, "image/png")},
        headers=headers,
    )
    assert response.status_code == 403
