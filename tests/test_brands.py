from uuid import uuid4

from tests.conftest import admin_headers, login_headers


def test_brand_crud_flow(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    brand_name = f"Nike-{uuid4().hex[:6]}"

    create = client.post(
        f"{api_prefix}/admin/brands",
        json={"name": brand_name},
        headers=admin,
    )
    assert create.status_code == 201
    created = create.json()["brand"]
    assert created["name"] == brand_name
    assert created["isActive"] is True
    brand_id = created["id"]

    listing = client.get(f"{api_prefix}/brands", headers=user_headers)
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] >= 1

    detail = client.get(f"{api_prefix}/brands/{brand_id}", headers=user_headers)
    assert detail.status_code == 200

    update = client.put(
        f"{api_prefix}/admin/brands/{brand_id}",
        json={"name": f"Adidas-{uuid4().hex[:6]}"},
        headers=admin,
    )
    assert update.status_code == 200
    assert update.json()["brand"]["name"].startswith("Adidas-")

    delete = client.delete(f"{api_prefix}/admin/brands/{brand_id}", headers=admin)
    assert delete.status_code == 200
    assert delete.json()["brand"]["deletedAt"] is not None

    after_delete = client.get(f"{api_prefix}/brands/{brand_id}", headers=user_headers)
    assert after_delete.status_code == 404


def test_brand_is_active_hides_from_public(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    name = f"HiddenBrand-{uuid4().hex[:6]}"

    created = client.post(f"{api_prefix}/admin/brands", json={"name": name}, headers=admin)
    assert created.status_code == 201
    brand_id = created.json()["brand"]["id"]

    deactivate = client.put(
        f"{api_prefix}/admin/brands/{brand_id}",
        json={"isActive": False},
        headers=admin,
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["brand"]["isActive"] is False

    public_list = client.get(f"{api_prefix}/brands", headers=user_headers)
    assert public_list.status_code == 200
    assert all(item["id"] != brand_id for item in public_list.json()["data"])

    public_detail = client.get(f"{api_prefix}/brands/{brand_id}", headers=user_headers)
    assert public_detail.status_code == 404


def test_brands_require_auth(client, api_prefix):
    response = client.post(f"{api_prefix}/admin/brands", json={"name": "Nike"})
    assert response.status_code == 401
