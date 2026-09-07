from uuid import uuid4

from tests.conftest import admin_headers, login_headers


def test_category_crud_flow(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_name = f"Electronics-{uuid4().hex[:6]}"

    create = client.post(
        f"{api_prefix}/admin/categories",
        json={"name": category_name},
        headers=admin,
    )
    assert create.status_code == 201
    created = create.json()["category"]
    assert created["name"] == category_name
    assert created["isActive"] is True
    category_id = created["id"]

    listing = client.get(f"{api_prefix}/categories", headers=user_headers)
    assert listing.status_code == 200
    assert listing.json()["meta"]["total"] >= 1

    detail = client.get(f"{api_prefix}/categories/{category_id}", headers=user_headers)
    assert detail.status_code == 200

    update = client.put(
        f"{api_prefix}/admin/categories/{category_id}",
        json={"name": "Gadgets"},
        headers=admin,
    )
    assert update.status_code == 200
    assert update.json()["category"]["name"] == "Gadgets"

    delete = client.delete(f"{api_prefix}/admin/categories/{category_id}", headers=admin)
    assert delete.status_code == 200
    assert delete.json()["category"]["deletedAt"] is not None

    after_delete = client.get(f"{api_prefix}/categories/{category_id}", headers=user_headers)
    assert after_delete.status_code == 404


def test_category_is_active_hides_from_public(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    name = f"Hidden-{uuid4().hex[:6]}"

    created = client.post(f"{api_prefix}/admin/categories", json={"name": name}, headers=admin)
    assert created.status_code == 201
    category_id = created.json()["category"]["id"]

    deactivate = client.put(
        f"{api_prefix}/admin/categories/{category_id}",
        json={"isActive": False},
        headers=admin,
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["category"]["isActive"] is False

    public_list = client.get(f"{api_prefix}/categories", headers=user_headers)
    assert public_list.status_code == 200
    assert all(item["id"] != category_id for item in public_list.json()["data"])

    public_detail = client.get(f"{api_prefix}/categories/{category_id}", headers=user_headers)
    assert public_detail.status_code == 404

    admin_detail = client.get(f"{api_prefix}/admin/categories/{category_id}", headers=admin)
    assert admin_detail.status_code == 200
    assert admin_detail.json()["category"]["isActive"] is False

    admin_inactive = client.get(
        f"{api_prefix}/admin/categories",
        params={"isActive": "false"},
        headers=admin,
    )
    assert admin_inactive.status_code == 200
    assert any(item["id"] == category_id for item in admin_inactive.json()["data"])


def test_categories_require_auth(client, api_prefix):
    response = client.post(f"{api_prefix}/admin/categories", json={"name": "Electronics"})
    assert response.status_code == 401


def test_category_search(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)

    for name in ["Electronics", "Books", "Electronic Accessories"]:
        client.post(f"{api_prefix}/admin/categories", json={"name": f"{name}-{uuid4().hex[:4]}"}, headers=admin)

    response = client.get(
        f"{api_prefix}/categories",
        params={"search": "elect"},
        headers=user_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] >= 2


def test_category_pagination(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)

    for index in range(1, 16):
        client.post(
            f"{api_prefix}/admin/categories",
            json={"name": f"Category {index:02d}-{uuid4().hex[:4]}"},
            headers=admin,
        )

    page_1 = client.get(
        f"{api_prefix}/categories",
        params={"page": 1, "limit": 10},
        headers=user_headers,
    )
    page_2 = client.get(
        f"{api_prefix}/categories",
        params={"page": 2, "limit": 10},
        headers=user_headers,
    )

    assert page_1.status_code == 200
    assert page_2.status_code == 200
    assert len(page_1.json()["data"]) == 10
    assert len(page_2.json()["data"]) >= 5
