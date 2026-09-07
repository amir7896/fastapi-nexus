from uuid import uuid4

from tests.conftest import (
    admin_headers,
    create_category,
    create_product,
    login_headers,
)
from tests.test_returns import _create_paid_order


def _token(headers: dict[str, str]) -> str:
    return headers["Authorization"].removeprefix("Bearer ")


def _receive_until(socket, event_type: str, *, attempts: int = 8) -> dict:
    for _ in range(attempts):
        payload = socket.receive_json()
        if payload.get("type") == event_type:
            return payload
    raise AssertionError(f"Did not receive {event_type}")


def test_customer_starts_general_issue_and_admin_replies(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)

    created = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "GENERAL", "subject": "Card declined", "message": "Checkout failed twice"},
        headers=user_headers,
    )
    assert created.status_code == 200, created.text
    conversation_id = created.json()["conversation"]["id"]
    assert created.json()["conversation"]["contextType"] == "GENERAL"

    inbox = client.get(f"{api_prefix}/support/conversations", headers=admin)
    assert inbox.status_code == 200
    assert inbox.json()["meta"]["total"] >= 1
    assert any(item["id"] == conversation_id for item in inbox.json()["data"])

    reply = client.post(
        f"{api_prefix}/support/conversations/{conversation_id}/messages",
        json={"body": "We can retry the charge — reply with the last 4."},
        headers=admin,
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["data"]["isStaff"] is True

    thread = client.get(
        f"{api_prefix}/support/conversations/{conversation_id}/messages",
        headers=user_headers,
    )
    assert thread.status_code == 200
    assert len(thread.json()["data"]) == 2
    unread = client.get(f"{api_prefix}/support/unread-count", headers=user_headers)
    assert unread.json()["count"] == 0


def test_product_support_reuses_same_thread(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    category_id = create_category(client, api_prefix, admin)
    product_id = create_product(client, api_prefix, admin, category_id, name="Trail pack")

    first = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "PRODUCT", "productId": product_id, "message": "Is this waterproof?"},
        headers=user_headers,
    )
    second = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "PRODUCT", "productId": product_id, "message": "Also, what size?"},
        headers=user_headers,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["conversation"]["id"] == second.json()["conversation"]["id"]
    assert first.json()["conversation"]["productName"] == "Trail pack"

    messages = client.get(
        f"{api_prefix}/support/conversations/{first.json()['conversation']['id']}/messages",
        headers=user_headers,
    )
    assert len(messages.json()["data"]) == 2


def test_order_support_is_owner_only(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    order = _create_paid_order(client, api_prefix, user_headers, admin)

    other = login_headers(
        client,
        api_prefix,
        {
            "name": "Other",
            "email": f"other-{uuid4().hex}@example.com",
            "password": "Secret123",
            "age": 22,
        },
    )
    blocked = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "ORDER", "orderId": order["id"], "message": "Where is this?"},
        headers=other,
    )
    assert blocked.status_code == 403

    started = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "ORDER", "orderId": order["id"], "message": "Need a different size"},
        headers=user_headers,
    )
    assert started.status_code == 200, started.text
    assert started.json()["conversation"]["orderId"] == order["id"]

    hidden = client.get(
        f"{api_prefix}/support/conversations/{started.json()['conversation']['id']}",
        headers=other,
    )
    assert hidden.status_code == 403


def test_support_socket_notifies_admin_and_customer(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)

    with client.websocket_connect(
        f"{api_prefix}/ws/notifications?token={_token(admin)}"
    ) as admin_socket:
        started = client.post(
            f"{api_prefix}/support/conversations",
            json={"contextType": "GENERAL", "subject": "Late delivery", "message": "Still waiting"},
            headers=user_headers,
        )
        assert started.status_code == 200, started.text
        incoming = _receive_until(admin_socket, "support.message")
        assert incoming["type"] == "support.message"
        assert incoming["message"]["body"] == "Still waiting"
        conversation_id = incoming["conversationId"]

        with client.websocket_connect(
            f"{api_prefix}/ws/notifications?token={_token(user_headers)}"
        ) as user_socket:
            reply = client.post(
                f"{api_prefix}/support/conversations/{conversation_id}/messages",
                json={"body": "Looking into the courier now"},
                headers=admin,
            )
            assert reply.status_code == 200, reply.text
            payload = _receive_until(user_socket, "support.message")
            assert payload["type"] == "support.message"
            assert payload["message"]["isStaff"] is True
            assert payload["message"]["body"] == "Looking into the courier now"


def test_support_message_is_marked_seen_when_other_side_opens_it(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    created = client.post(
        f"{api_prefix}/support/conversations",
        json={"contextType": "GENERAL", "subject": "Wrong size", "message": "Can I exchange?"},
        headers=user_headers,
    )
    conversation_id = created.json()["conversation"]["id"]
    first_id = client.get(
        f"{api_prefix}/support/conversations/{conversation_id}/messages",
        headers=user_headers,
    ).json()["data"][0]["id"]
    before = client.get(
        f"{api_prefix}/support/conversations/{conversation_id}/messages",
        headers=user_headers,
    )
    assert before.json()["data"][0]["seenAt"] is None

    opened = client.post(
        f"{api_prefix}/support/conversations/{conversation_id}/read",
        headers=admin,
    )
    assert opened.status_code == 200, opened.text

    after = client.get(
        f"{api_prefix}/support/conversations/{conversation_id}/messages",
        headers=user_headers,
    )
    assert after.json()["data"][0]["id"] == first_id
    assert after.json()["data"][0]["seenAt"] is not None


def test_support_presence_lists_connected_admin(client, api_prefix, signup_payload):
    user_headers = login_headers(client, api_prefix, signup_payload)
    admin = admin_headers(client, api_prefix)
    offline = client.get(f"{api_prefix}/support/presence", headers=user_headers)
    assert offline.status_code == 200
    assert offline.json()["supportOnline"] is False

    admin_id = client.get(f"{api_prefix}/auth/me", headers=admin).json()["id"]
    with client.websocket_connect(f"{api_prefix}/ws/notifications?token={_token(admin)}"):
        online = client.get(f"{api_prefix}/support/presence", headers=user_headers)
        assert online.json()["supportOnline"] is True
        assert admin_id in online.json()["onlineUserIds"]
