from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.api.deps import CurrentUserDep, DbSession, InboxNotificationServiceDep
from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.repositories.user_repository import UserRepository
from app.schemas.common import MessageResponse
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_hub import hub, notify_presence

logger = get_logger(__name__)

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(current_user: CurrentUserDep, inbox: InboxNotificationServiceDep):
    return inbox.list_for(current_user)


@router.patch("/notifications/read-all", response_model=MessageResponse)
def mark_all_notifications_read(current_user: CurrentUserDep, inbox: InboxNotificationServiceDep):
    return inbox.mark_all_read(current_user=current_user)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    current_user: CurrentUserDep,
    inbox: InboxNotificationServiceDep,
):
    return inbox.mark_read(notification_id, current_user=current_user)


def _user_from_token(db: Session, token: str | None):
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        return None
    return UserRepository(db).get_by_id(user_id)


@router.websocket("/ws/notifications")
async def notifications_socket(
    websocket: WebSocket,
    db: DbSession,
    token: str | None = Query(default=None),
) -> None:
    user = _user_from_token(db, token)
    if user is None:
        await websocket.close(code=4401)
        return

    await hub.connect(user.id, websocket, is_admin=user.can_manage_support)
    notify_presence(exclude=user.id)
    logger.info("Notification socket connected for user %s", user.id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        went_offline = hub.disconnect(user.id, websocket)
        if went_offline:
            notify_presence()
        logger.info("Notification socket disconnected for user %s", user.id)
