from tests.conftest import admin_headers, login_headers
from tests.test_returns import _create_paid_order, _ship


def test_review_only_after_delivered(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    product_id = order["items"][0]["productId"]

    blocked = client.post(
        f"{api_prefix}/reviews/products/{product_id}",
        json={"rating": 5, "comment": "Great item"},
        headers=user_headers,
    )
    assert blocked.status_code == 400

    _ship(client, api_prefix, admin, order["id"])
    client.post(f"{api_prefix}/orders/{order['id']}/received", headers=user_headers)

    created = client.post(
        f"{api_prefix}/reviews/products/{product_id}",
        json={"rating": 5, "title": "Solid", "comment": "Arrived in good shape"},
        headers=user_headers,
    )
    assert created.status_code == 200, created.text
    assert created.json()["review"]["rating"] == 5

    listing = client.get(f"{api_prefix}/reviews/products/{product_id}")
    assert listing.status_code == 200
    assert listing.json()["reviewCount"] == 1
    assert listing.json()["data"][0]["comment"] == "Arrived in good shape"

    eligibility = client.get(
        f"{api_prefix}/reviews/products/{product_id}/eligibility",
        headers=user_headers,
    )
    assert eligibility.json()["eligibility"]["reason"] == "already_reviewed"
    assert eligibility.json()["eligibility"]["canReview"] is True


def test_order_review_targets_after_delivery(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)
    empty = client.get(f"{api_prefix}/reviews/orders/{order['id']}/targets", headers=user_headers)
    assert empty.status_code == 200
    assert empty.json()["data"] == []

    _ship(client, api_prefix, admin, order["id"])
    client.post(f"{api_prefix}/orders/{order['id']}/received", headers=user_headers)
    targets = client.get(f"{api_prefix}/reviews/orders/{order['id']}/targets", headers=user_headers)
    assert targets.status_code == 200
    assert len(targets.json()["data"]) == 1
    assert targets.json()["data"][0]["canReview"] is True
