from unittest.mock import MagicMock

from tests.conftest import admin_headers, create_category, create_product, login_headers, order_payload


def _shipping():
    return {
        "name": "Amir Shahzad",
        "phoneCountryCode": "+92",
        "phone": "3001234567",
        "address": "Street 1",
        "city": "Lahore",
        "state": "Punjab",
        "country": "Pakistan",
    }


def test_coupon_crud_preview_checkout_and_partial_refund(client, api_prefix, signup_payload, monkeypatch):
    monkeypatch.setattr(
        "app.services.stripe_payment_service.stripe.Refund.create",
        MagicMock(return_value=MagicMock(id="re_test_partial")),
    )
    admin = admin_headers(client, api_prefix)
    created = client.post(
        f"{api_prefix}/admin/coupons",
        json={"code": "save10", "type": "percent", "value": "10", "isActive": True},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    coupon = created.json()["coupon"]
    assert coupon["code"] == "SAVE10"
    coupon_id = coupon["id"]

    listed = client.get(f"{api_prefix}/admin/coupons", headers=admin)
    assert listed.status_code == 200, listed.text
    assert coupon_id in [item["id"] for item in listed.json()["data"]]

    preview = client.get(f"{api_prefix}/coupons/preview", params={"code": "SAVE10", "subtotal": "40.00"})
    assert preview.status_code == 200, preview.text
    assert preview.json()["discount"] in ("4.00", "4.0")

    user = login_headers(client, api_prefix, signup_payload)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, price="40.00", stock=8)
    order = client.post(
        f"{api_prefix}/orders",
        json={**order_payload(product_id), "shipping": _shipping(), "couponCode": "SAVE10"},
        headers=user,
    )
    assert order.status_code == 201, order.text
    body = order.json()["order"]
    assert body["couponCode"] == "SAVE10"
    assert float(body["discountAmount"]) == 4

    refunded = client.post(
        f"{api_prefix}/admin/orders/{body['id']}/refund",
        json={"amount": "2.00"},
        headers=admin,
    )
    assert refunded.status_code == 200, refunded.text
    assert float(refunded.json()["order"]["amountRefunded"]) == 2

    toggled = client.patch(
        f"{api_prefix}/admin/coupons/{coupon_id}",
        json={"isActive": False},
        headers=admin,
    )
    assert toggled.status_code == 200, toggled.text
    assert toggled.json()["coupon"]["isActive"] is False

    deleted = client.delete(f"{api_prefix}/admin/coupons/{coupon_id}", headers=admin)
    assert deleted.status_code == 200, deleted.text
