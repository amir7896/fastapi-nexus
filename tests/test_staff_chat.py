from uuid import uuid4

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from tests.conftest import auth_headers, login_headers


def _create_verified_user(*, name: str, role: UserRole) -> tuple[str, str]:
    email = f"{role.value.lower()}-{uuid4().hex}@gmail.com"
    password = "Secret123"
    db = SessionLocal()
    try:
        UserRepository(db).create(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            email_verified=True,
        )
    finally:
        db.close()
    return email, password


def _staff_headers(client, api_prefix: str, role: UserRole, name: str) -> dict[str, str]:
    email, password = _create_verified_user(name=name, role=role)
    token = client.post(
        f"{api_prefix}/auth/admin/login",
        json={"email": email, "password": password},
    ).json()["access_token"]
    return auth_headers(token)


def test_staff_can_start_private_team_chat(client, api_prefix):
    admin = _staff_headers(client, api_prefix, UserRole.ADMIN, "Ada Admin")
    manager = _staff_headers(client, api_prefix, UserRole.MANAGER, "Mo Manager")

    colleagues = client.get(f"{api_prefix}/support/colleagues", headers=admin)
    assert colleagues.status_code == 200, colleagues.text
    peer = next(item for item in colleagues.json()["data"] if item["role"] == "MANAGER")

    started = client.post(
        f"{api_prefix}/support/team/conversations",
        json={"peerId": peer["id"], "message": "Can you check today's refunds?"},
        headers=admin,
    )
    assert started.status_code == 200, started.text
    conversation = started.json()["conversation"]
    assert conversation["channel"] == "STAFF"
    assert conversation["peerName"] == "Mo Manager"
    conversation_id = conversation["id"]

    inbox = client.get(f"{api_prefix}/support/conversations?channel=STAFF", headers=manager)
    assert inbox.status_code == 200, inbox.text
    assert any(item["id"] == conversation_id for item in inbox.json()["data"])

    customer_inbox = client.get(f"{api_prefix}/support/conversations", headers=admin)
    assert customer_inbox.status_code == 200
    assert all(item["id"] != conversation_id for item in customer_inbox.json()["data"])

    reply = client.post(
        f"{api_prefix}/support/conversations/{conversation_id}/messages",
        json={"body": "On it."},
        headers=manager,
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["data"]["senderName"] == "Mo Manager"

    reused = client.post(
        f"{api_prefix}/support/team/conversations",
        json={"peerId": peer["id"], "message": "Thanks"},
        headers=admin,
    )
    assert reused.status_code == 200, reused.text
    assert reused.json()["conversation"]["id"] == conversation_id


def test_customer_cannot_use_team_chat(client, api_prefix, signup_payload):
    customer = login_headers(client, api_prefix, signup_payload)
    admin = _staff_headers(client, api_prefix, UserRole.ADMIN, "Admin")
    admin_id = client.get(f"{api_prefix}/auth/me", headers=admin).json()["id"]

    listed = client.get(f"{api_prefix}/support/conversations?channel=STAFF", headers=customer)
    assert listed.status_code == 403

    colleagues = client.get(f"{api_prefix}/support/colleagues", headers=customer)
    assert colleagues.status_code == 403

    started = client.post(
        f"{api_prefix}/support/team/conversations",
        json={"peerId": admin_id, "message": "Hi"},
        headers=customer,
    )
    assert started.status_code == 403


def test_other_staff_cannot_open_private_team_chat(client, api_prefix):
    finance = _staff_headers(client, api_prefix, UserRole.FINANCE, "Fay Finance")
    support = _staff_headers(client, api_prefix, UserRole.SUPPORT, "Sam Support")
    fulfillment = _staff_headers(client, api_prefix, UserRole.FULFILLMENT, "Flo Fulfillment")

    peer_id = client.get(f"{api_prefix}/auth/me", headers=support).json()["id"]
    started = client.post(
        f"{api_prefix}/support/team/conversations",
        json={"peerId": peer_id, "message": "Need a refund id"},
        headers=finance,
    )
    assert started.status_code == 200, started.text
    conversation_id = started.json()["conversation"]["id"]

    outsider = client.get(
        f"{api_prefix}/support/conversations/{conversation_id}",
        headers=fulfillment,
    )
    assert outsider.status_code == 403
