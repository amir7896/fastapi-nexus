from uuid import UUID, uuid4

import pytest
from starlette.websockets import WebSocketDisconnect

from app.models.order import OrderStatus
from app.services.notification_hub import notify_order_status
from tests.conftest import mark_email_verified


def _login_token(client, api_prefix: str, signup_payload: dict) -> tuple[str, str]:
    client.post(f"{api_prefix}/auth/signup", json=signup_payload)
    mark_email_verified(signup_payload["email"])
    body = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": signup_payload["email"],
            "password": signup_payload["password"],
        },
    ).json()
    return body["access_token"], body["user"]["id"]


def test_notifications_socket_rejects_missing_token(client, api_prefix):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"{api_prefix}/ws/notifications"):
            pass
    assert error.value.code == 4401


def test_notifications_socket_rejects_invalid_token(client, api_prefix):
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(f"{api_prefix}/ws/notifications?token=not-a-jwt"):
            pass
    assert error.value.code == 4401


def test_notifications_socket_sends_order_status(client, api_prefix, signup_payload):
    token, user_id = _login_token(client, api_prefix, signup_payload)
    order_id = uuid4()

    with client.websocket_connect(f"{api_prefix}/ws/notifications?token={token}") as socket:
        notify_order_status(
            user_id=UUID(user_id),
            order_id=order_id,
            order_number=1061,
            status=OrderStatus.SHIPPED,
        )
        payload = socket.receive_json()

    assert payload == {
        "type": "order.status",
        "orderId": str(order_id),
        "orderNumber": 1061,
        "status": "SHIPPED",
    }
