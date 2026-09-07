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

    async def connect(self, user_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: UUID, payload: dict) -> None:
        for websocket in list(self._connections.get(user_id, ())):
            if websocket.client_state is not WebSocketState.CONNECTED:
                self.disconnect(user_id, websocket)
                continue
            try:
                await websocket.send_json(payload)
            except (WebSocketDisconnect, RuntimeError):
                self.disconnect(user_id, websocket)

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
    try:
        loop = _loop
        if loop is None or not loop.is_running():
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.warning("Skipped order status notify; no event loop")
                return
            loop.create_task(hub.send_to_user(user_id, payload))
            return
        asyncio.run_coroutine_threadsafe(hub.send_to_user(user_id, payload), loop)
    except Exception:
        logger.exception("Failed to notify user %s of order status", user_id)
