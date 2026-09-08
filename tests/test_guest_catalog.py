from tests.conftest import admin_headers, create_brand, create_category, create_product


def test_guest_can_browse_catalog_and_store(client, api_prefix):
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin, name="Guest-Cat")
    brand_id = create_brand(client, api_prefix, admin, name="Guest-Brand")
    product_id = create_product(client, api_prefix, admin, category_id, name="Guest-Tee")

    store = client.get(f"{api_prefix}/organizations/public")
    assert store.status_code == 200, store.text
    assert store.json()["store"]["slug"]

    products = client.get(f"{api_prefix}/products")
    assert products.status_code == 200, products.text
    ids = [item["id"] for item in products.json()["data"]]
    assert product_id in ids

    product = client.get(f"{api_prefix}/products/{product_id}")
    assert product.status_code == 200, product.text
    assert product.json()["product"]["id"] == product_id

    categories = client.get(f"{api_prefix}/categories")
    assert categories.status_code == 200, categories.text
    assert category_id in [item["id"] for item in categories.json()["data"]]

    brands = client.get(f"{api_prefix}/brands")
    assert brands.status_code == 200, brands.text
    assert brand_id in [item["id"] for item in brands.json()["data"]]

    cart = client.get(f"{api_prefix}/cart")
    assert cart.status_code == 401


def test_user_can_update_email_alert_preferences(client, api_prefix, signup_payload):
    from tests.conftest import login_headers

    headers = login_headers(client, api_prefix, signup_payload)
    me = client.post(
        f"{api_prefix}/auth/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    ).json()["user"]
    updated = client.put(
        f"{api_prefix}/users/{me['id']}",
        json={
            "name": me["name"],
            "age": me.get("age") or 25,
            "notifyOrderEmail": False,
            "notifySupportEmail": False,
            "notifyMarketingEmail": True,
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    user = updated.json()["user"]
    assert user["notifyOrderEmail"] is False
    assert user["notifySupportEmail"] is False
    assert user["notifyMarketingEmail"] is True
