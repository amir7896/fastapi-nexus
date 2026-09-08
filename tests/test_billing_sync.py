from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.organization_repository import OrganizationRepository
from tests.test_organizations import _merchant_headers


def test_billing_saves_pro_plan_from_stripe_subscription(client, api_prefix, monkeypatch):
    captured: dict = {}

    def capture_invite(self, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(
        "app.services.email_service.EmailService.send_staff_invite",
        capture_invite,
    )
    settings = get_settings()
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(settings, "STRIPE_PRICE_PRO", "price_pro_test")
    monkeypatch.setattr(settings, "STRIPE_PRICE_BUSINESS", "price_biz_test")

    headers = _merchant_headers(client, api_prefix, f"Billing Sync {uuid4().hex[:6]}")
    me = client.get(f"{api_prefix}/organizations/current", headers=headers)
    assert me.status_code == 200, me.text
    org_id = me.json()["organization"]["id"]

    db = SessionLocal()
    try:
        org = OrganizationRepository(db).get_by_id(UUID(org_id))
        assert org is not None
        org.plan = "free"
        org.stripe_billing_customer_id = "cus_billing_sync"
        db.add(org)
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr(
        "app.services.organization_service.stripe.Invoice.list",
        MagicMock(return_value=MagicMock(data=[])),
    )
    monkeypatch.setattr(
        "app.services.organization_service.stripe.Subscription.list",
        MagicMock(
            return_value=MagicMock(
                data=[
                    SimpleNamespace(
                        id="sub_pro",
                        status="active",
                        metadata={"plan": "pro"},
                        items=SimpleNamespace(
                            data=[SimpleNamespace(price=SimpleNamespace(id="price_pro_test"))]
                        ),
                    )
                ]
            )
        ),
    )

    billing = client.get(f"{api_prefix}/organizations/billing", headers=headers)
    assert billing.status_code == 200, billing.text
    body = billing.json()
    assert body["plan"] == "pro"
    assert body["planStatus"] == "active"
    assert next(item["current"] for item in body["plans"] if item["id"] == "pro") is True
