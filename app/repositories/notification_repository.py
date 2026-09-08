from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        title: str,
        description: str,
        type: str,
        order_id: UUID | None = None,
        product_id: UUID | None = None,
        conversation_id: UUID | None = None,
    ) -> Notification:
        row = Notification(
            user_id=user_id,
            organization_id=organization_id,
            title=title,
            description=description,
            type=type,
            order_id=order_id,
            product_id=product_id,
            conversation_id=conversation_id,
            is_read=False,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def list_for_user(self, user_id: UUID, *, limit: int = 50) -> list[Notification]:
        return list(
            self._db.scalars(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc())
                .limit(limit)
            ).all()
        )

    def unread_count(self, user_id: UUID) -> int:
        return int(
            self._db.scalar(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
            or 0
        )

    def find_open_duplicate(
        self,
        *,
        user_id: UUID,
        type: str,
        order_id: UUID | None = None,
        product_id: UUID | None = None,
    ) -> Notification | None:
        if order_id is None and product_id is None:
            return None
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.type == type,
            Notification.is_read.is_(False),
        )
        if order_id is not None:
            stmt = stmt.where(Notification.order_id == order_id)
        if product_id is not None:
            stmt = stmt.where(Notification.product_id == product_id)
        return self._db.scalar(stmt.limit(1))

    def get_for_user(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        return self._db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )

    def mark_read(self, row: Notification) -> Notification:
        row.is_read = True
        self._db.commit()
        self._db.refresh(row)
        return row

    def mark_all_read(self, user_id: UUID) -> int:
        result = self._db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        self._db.commit()
        return int(result.rowcount or 0)
