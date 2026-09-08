import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.core.logging import get_logger
from app.models.order import OrderStatus

logger = get_logger(__name__)

_loop: asyncio.AbstractEventLoop | None = None


class NotificationHub:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._admin_ids: set[UUID] = set()

    async def connect(self, user_id: UUID, websocket: WebSocket, *, is_admin: bool = False) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)
        if is_admin:
            self._admin_ids.add(user_id)

    @property
    def admin_ids(self) -> set[UUID]:
        return set(self._admin_ids)

    @property
    def online_ids(self) -> set[UUID]:
        return set(self._connections)

    def is_online(self, user_id: UUID) -> bool:
        return user_id in self._connections

    @property
    def support_online(self) -> bool:
        return bool(self._admin_ids)

    def presence_payload(self, event_type: str = "presence.update") -> dict:
        return {
            "type": event_type,
            "supportOnline": self.support_online,
            "onlineUserIds": [str(user_id) for user_id in self._connections],
        }

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> bool:
        sockets = self._connections.get(user_id)
        if not sockets:
            return False
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)
            self._admin_ids.discard(user_id)
            return True
        return False

    async def send_to_user(self, user_id: UUID, payload: dict) -> None:
        for websocket in list(self._connections.get(user_id, ())):
            if websocket.client_state is not WebSocketState.CONNECTED:
                self.disconnect(user_id, websocket)
                continue
            try:
                await websocket.send_json(payload)
            except (WebSocketDisconnect, RuntimeError):
                self.disconnect(user_id, websocket)

    async def send_to_users(self, user_ids: set[UUID], payload: dict) -> None:
        for user_id in user_ids:
            await self.send_to_user(user_id, payload)

    async def close_all(self) -> None:
        for user_id, sockets in list(self._connections.items()):
            for websocket in list(sockets):
                try:
                    if websocket.client_state is WebSocketState.CONNECTED:
                        await websocket.close()
                except RuntimeError:
                    pass
                self.disconnect(user_id, websocket)


hub = NotificationHub()


def bind_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def _schedule(coro, *, warning: str) -> None:
    try:
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None:
            running.create_task(coro)
            return
        loop = _loop
        if loop is None or not loop.is_running():
            logger.warning(warning)
            return
        asyncio.run_coroutine_threadsafe(coro, loop)
    except Exception:
        logger.exception("Failed to schedule notification")


def notify_order_status(
    *,
    user_id: UUID,
    order_id: UUID,
    order_number: int,
    status: OrderStatus,
) -> None:
    payload = {
        "type": "order.status",
        "orderId": str(order_id),
        "orderNumber": order_number,
        "status": status.value,
    }
    _schedule(
        hub.send_to_user(user_id, payload),
        warning="Skipped order status notify; no event loop",
    )


def notify_support_message(
    *,
    customer_id: UUID,
    payload: dict,
    recipients: set[UUID] | None = None,
) -> None:
    targets = recipients if recipients is not None else hub.admin_ids | {customer_id}
    _schedule(
        hub.send_to_users(targets, payload),
        warning="Skipped support message notify; no event loop",
    )


def notify_support_seen(
    *,
    customer_id: UUID,
    payload: dict,
    recipients: set[UUID] | None = None,
) -> None:
    notify_support_message(customer_id=customer_id, payload=payload, recipients=recipients)


def notify_presence(*, exclude: UUID | None = None) -> None:
    recipients = hub.online_ids
    if exclude is not None:
        recipients.discard(exclude)
    if not recipients:
        return
    _schedule(
        hub.send_to_users(recipients, hub.presence_payload()),
        warning="Skipped presence notify; no event loop",
    )
