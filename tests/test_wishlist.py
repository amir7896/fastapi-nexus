from uuid import uuid4

from tests.conftest import admin_headers, create_category, create_product, login_headers


def test_wishlist_add_list_and_remove(client, api_prefix, signup_payload):
    user = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, name="Wishlist Lamp")

    empty = client.get(f"{api_prefix}/wishlist", headers=user)
    assert empty.status_code == 200
    assert empty.json()["data"] == []
    assert empty.json()["ids"] == []

    added = client.post(f"{api_prefix}/wishlist", json={"productId": product_id}, headers=user)
    assert added.status_code == 201, added.text
    assert added.json()["product"]["id"] == product_id
    assert product_id in added.json()["ids"]

    again = client.post(f"{api_prefix}/wishlist", json={"productId": product_id}, headers=user)
    assert again.status_code == 201
    assert again.json()["ids"].count(product_id) == 1

    listing = client.get(f"{api_prefix}/wishlist", headers=user)
    assert listing.status_code == 200
    assert listing.json()["data"][0]["name"] == "Wishlist Lamp"

    ids = client.get(f"{api_prefix}/wishlist/ids", headers=user)
    assert ids.status_code == 200
    assert ids.json()["ids"] == [product_id]

    removed = client.delete(f"{api_prefix}/wishlist/{product_id}", headers=user)
    assert removed.status_code == 200
    assert removed.json()["ids"] == []

    missing = client.delete(f"{api_prefix}/wishlist/{product_id}", headers=user)
    assert missing.status_code == 404


def test_wishlist_rejects_unknown_product_and_stays_private(client, api_prefix, signup_payload):
    user = login_headers(client, api_prefix, signup_payload)
    other = login_headers(
        client,
        api_prefix,
        {
            "name": "Other",
            "email": f"other-{uuid4().hex}@gmail.com",
            "password": "Secret123",
            "age": 28,
        },
    )
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id)

    unknown = client.post(
        f"{api_prefix}/wishlist",
        json={"productId": str(uuid4())},
        headers=user,
    )
    assert unknown.status_code == 404

    saved = client.post(f"{api_prefix}/wishlist", json={"productId": product_id}, headers=user)
    assert saved.status_code == 201

    other_list = client.get(f"{api_prefix}/wishlist", headers=other)
    assert other_list.status_code == 200
    assert other_list.json()["data"] == []


def test_wishlist_requires_auth(client, api_prefix):
    response = client.get(f"{api_prefix}/wishlist")
    assert response.status_code == 401
