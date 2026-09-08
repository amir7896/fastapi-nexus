from uuid import uuid4

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.notification import NotificationType
from app.repositories.notification_repository import NotificationRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from tests.conftest import login_headers


def _seed_notification(user_id, organization_id, *, title: str, type: str = NotificationType.GENERAL.value):
    db = SessionLocal()
    try:
        return NotificationRepository(db).create(
            user_id=user_id,
            organization_id=organization_id,
            title=title,
            description=f"{title} details",
            type=type,
        )
    finally:
        db.close()


def test_inbox_list_mark_one_and_mark_all(client, api_prefix, signup_payload):
    headers = login_headers(client, api_prefix, signup_payload)
    db = SessionLocal()
    try:
        user = UserRepository(db).get_by_email(signup_payload["email"])
        assert user is not None
        org = OrganizationRepository(db).get_by_slug(get_settings().DEFAULT_ORGANIZATION_SLUG)
        assert org is not None
        user_id = user.id
        organization_id = org.id
    finally:
        db.close()

    first = _seed_notification(user_id, organization_id, title="Order placed successfully", type="order_placed")
    second = _seed_notification(user_id, organization_id, title="Your order has shipped", type="order_shipped")

    listed = client.get(f"{api_prefix}/notifications", headers=headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["unreadCount"] == 2
    ids = {item["id"] for item in body["data"]}
    assert str(first.id) in ids
    assert str(second.id) in ids
    assert all(item["isRead"] is False for item in body["data"])

    marked = client.patch(f"{api_prefix}/notifications/{first.id}/read", headers=headers)
    assert marked.status_code == 200, marked.text
    assert marked.json()["notification"]["isRead"] is True

    after_one = client.get(f"{api_prefix}/notifications", headers=headers).json()
    assert after_one["unreadCount"] == 1

    all_read = client.patch(f"{api_prefix}/notifications/read-all", headers=headers)
    assert all_read.status_code == 200, all_read.text

    after_all = client.get(f"{api_prefix}/notifications", headers=headers).json()
    assert after_all["unreadCount"] == 0
    assert all(item["isRead"] is True for item in after_all["data"])


def test_inbox_does_not_leak_another_users_notifications(client, api_prefix, signup_payload):
    headers = login_headers(client, api_prefix, signup_payload)
    other_payload = {
        "name": "Other",
        "email": f"other-{uuid4().hex}@gmail.com",
        "password": "Secret123",
        "age": 26,
    }
    login_headers(client, api_prefix, other_payload)

    db = SessionLocal()
    try:
        other = UserRepository(db).get_by_email(other_payload["email"])
        org = OrganizationRepository(db).get_by_slug(get_settings().DEFAULT_ORGANIZATION_SLUG)
        assert other is not None and org is not None
        other_id = other.id
        organization_id = org.id
    finally:
        db.close()

    _seed_notification(other_id, organization_id, title="Hidden")

    listed = client.get(f"{api_prefix}/notifications", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["unreadCount"] == 0
    assert listed.json()["data"] == []
