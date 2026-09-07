from io import BytesIO
from unittest.mock import MagicMock

from PIL import Image

from app.core.config import get_settings
from app.helpers.image_types import StoredImage
from tests.conftest import admin_headers, create_category, create_product, login_headers


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(32, 101, 209)).save(buffer, format="PNG")
    return buffer.getvalue()


def _image_file(name: str = "shoe.png"):
    return {"file": (name, BytesIO(_png_bytes()), "image/png")}


def test_user_cannot_upload_product_image(client, api_prefix, signup_payload):
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)
    user = login_headers(client, api_prefix, signup_payload)

    response = client.post(
        f"{api_prefix}/admin/products/{product_id}/image",
        files=_image_file(),
        headers=user,
    )
    assert response.status_code == 403


def test_upload_requires_storage_provider(client, api_prefix, monkeypatch):
    monkeypatch.setenv("IMAGE_STORAGE_PROVIDER", "")
    get_settings.cache_clear()
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    response = client.post(
        f"{api_prefix}/admin/products/{product_id}/image",
        files=_image_file(),
        headers=admin,
    )
    assert response.status_code == 400
    assert "IMAGE_STORAGE_PROVIDER" in response.json()["detail"]
    get_settings.cache_clear()


def test_upload_and_replace_product_image(client, api_prefix, monkeypatch):
    monkeypatch.setenv("IMAGE_STORAGE_PROVIDER", "cloudinary")
    get_settings.cache_clear()
    upload = MagicMock(
        side_effect=[
            StoredImage(
                url="https://cdn.example/one.jpg",
                public_id="Nexus/products/one",
                provider="cloudinary",
            ),
            StoredImage(
                url="https://cdn.example/two.jpg",
                public_id="Nexus/products/two",
                provider="cloudinary",
            ),
        ]
    )
    delete = MagicMock()
    monkeypatch.setattr("app.services.image_storage_service.upload_product_image", upload)
    monkeypatch.setattr("app.services.image_storage_service.delete_product_image", delete)

    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    first = client.post(
        f"{api_prefix}/admin/products/{product_id}/image",
        files=_image_file(),
        headers=admin,
    )
    assert first.status_code == 200
    assert first.json()["product"]["imageUrl"] == "https://cdn.example/one.jpg"

    second = client.post(
        f"{api_prefix}/admin/products/{product_id}/image",
        files=_image_file("other.png"),
        headers=admin,
    )
    assert second.status_code == 200
    assert second.json()["product"]["imageUrl"] == "https://cdn.example/two.jpg"
    delete.assert_called_once_with("Nexus/products/one")

    removed = client.delete(
        f"{api_prefix}/admin/products/{product_id}/image",
        headers=admin,
    )
    assert removed.status_code == 200
    assert removed.json()["product"]["imageUrl"] is None
    assert delete.call_count == 2
    get_settings.cache_clear()
