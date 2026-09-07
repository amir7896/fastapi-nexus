from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.support import SupportConversation, SupportConversationStatus, SupportContextType, SupportMessage
from app.models.user import User


class SupportRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_conversation(self, conversation_id: UUID) -> SupportConversation | None:
        return self._db.scalar(
            select(SupportConversation).where(SupportConversation.id == conversation_id)
        )

    def find_for_context(
        self,
        *,
        user_id: UUID,
        context_type: SupportContextType,
        order_id: UUID | None = None,
        product_id: UUID | None = None,
    ) -> SupportConversation | None:
        context = context_type.value
        if context == SupportContextType.GENERAL.value:
            return None
        filters = [
            SupportConversation.user_id == user_id,
            SupportConversation.context_type == context,
        ]
        if context == SupportContextType.ORDER.value:
            filters.append(SupportConversation.order_id == order_id)
        if context == SupportContextType.PRODUCT.value:
            filters.append(SupportConversation.product_id == product_id)
        return self._db.scalar(
            select(SupportConversation)
            .where(*filters)
            .order_by(SupportConversation.updated_at.desc())
            .limit(1)
        )

    def list_conversations(
        self,
        *,
        page: int,
        limit: int,
        user_id: UUID | None = None,
        status: SupportConversationStatus | None = None,
        context_type: SupportContextType | None = None,
        search: str | None = None,
    ) -> tuple[list[SupportConversation], int]:
        filters = []
        if user_id is not None:
            filters.append(SupportConversation.user_id == user_id)
        if status is not None:
            filters.append(SupportConversation.status == status.value)
        if context_type is not None:
            filters.append(SupportConversation.context_type == context_type.value)
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    SupportConversation.subject.ilike(pattern),
                    User.name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        count_stmt = select(func.count(SupportConversation.id)).select_from(SupportConversation)
        list_stmt = select(SupportConversation)
        if search:
            count_stmt = count_stmt.join(User, User.id == SupportConversation.user_id)
            list_stmt = list_stmt.join(User, User.id == SupportConversation.user_id)
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = self._db.scalar(count_stmt) or 0
        offset = (page - 1) * limit
        items = list(
            self._db.scalars(
                list_stmt.order_by(
                    SupportConversation.last_message_at.desc(),
                    SupportConversation.updated_at.desc(),
                )
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, total

    def unread_count(self, *, user_id: UUID, is_staff: bool) -> int:
        filters = [
            SupportMessage.seen_at.is_(None),
            SupportMessage.is_staff.is_(False) if is_staff else SupportMessage.is_staff.is_(True),
        ]
        stmt = select(func.count(SupportMessage.id)).select_from(SupportMessage)
        if not is_staff:
            stmt = stmt.join(
                SupportConversation,
                SupportConversation.id == SupportMessage.conversation_id,
            ).where(SupportConversation.user_id == user_id, *filters)
        else:
            stmt = stmt.where(*filters)
        return self._db.scalar(stmt) or 0

    def unread_message_counts(
        self,
        conversation_ids: list[UUID],
        *,
        reader_is_staff: bool,
    ) -> dict[UUID, int]:
        if not conversation_ids:
            return {}
        rows = self._db.execute(
            select(SupportMessage.conversation_id, func.count(SupportMessage.id)).where(
                SupportMessage.conversation_id.in_(conversation_ids),
                SupportMessage.seen_at.is_(None),
                SupportMessage.is_staff.is_(False) if reader_is_staff else SupportMessage.is_staff.is_(True),
            ).group_by(SupportMessage.conversation_id)
        ).all()
        return {conversation_id: count for conversation_id, count in rows}

    def create_conversation(
        self,
        *,
        user_id: UUID,
        context_type: SupportContextType,
        subject: str,
        order_id: UUID | None,
        product_id: UUID | None,
    ) -> SupportConversation:
        now = datetime.now(timezone.utc)
        conversation = SupportConversation(
            user_id=user_id,
            status=SupportConversationStatus.OPEN.value,
            context_type=context_type.value,
            order_id=order_id,
            product_id=product_id,
            subject=subject,
            created_at=now,
            updated_at=now,
        )
        self._db.add(conversation)
        self._db.commit()
        self._db.refresh(conversation)
        return conversation

    def add_message(
        self,
        conversation: SupportConversation,
        *,
        sender_id: UUID,
        body: str,
        is_staff: bool,
    ) -> SupportMessage:
        now = datetime.now(timezone.utc)
        message = SupportMessage(
            conversation_id=conversation.id,
            sender_id=sender_id,
            body=body,
            is_staff=is_staff,
            created_at=now,
        )
        conversation.last_message_preview = body[:200]
        conversation.last_message_at = now
        conversation.last_sender_id = sender_id
        conversation.last_sender_is_staff = is_staff
        conversation.status = SupportConversationStatus.OPEN.value
        conversation.updated_at = now
        if is_staff:
            conversation.staff_last_read_at = now
        else:
            conversation.customer_last_read_at = now
        self._db.add(message)
        self._db.commit()
        self._db.refresh(message)
        self._db.refresh(conversation)
        return message

    def mark_read(self, conversation: SupportConversation, *, is_staff: bool) -> SupportConversation:
        now = datetime.now(timezone.utc)
        if is_staff:
            conversation.staff_last_read_at = now
        else:
            conversation.customer_last_read_at = now
        conversation.updated_at = now
        self._db.commit()
        self._db.refresh(conversation)
        return conversation

    def mark_messages_seen(self, conversation_id: UUID, *, reader_is_staff: bool) -> list[SupportMessage]:
        filters = [
            SupportMessage.conversation_id == conversation_id,
            SupportMessage.seen_at.is_(None),
            SupportMessage.is_staff.is_(False) if reader_is_staff else SupportMessage.is_staff.is_(True),
        ]
        items = list(self._db.scalars(select(SupportMessage).where(*filters)).all())
        if not items:
            return []
        now = datetime.now(timezone.utc)
        for item in items:
            item.seen_at = now
        self._db.commit()
        for item in items:
            self._db.refresh(item)
        return items

    def set_status(
        self,
        conversation: SupportConversation,
        status: SupportConversationStatus,
    ) -> SupportConversation:
        conversation.status = status.value
        conversation.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(conversation)
        return conversation

    def list_messages(
        self,
        conversation_id: UUID,
        *,
        page: int,
        limit: int,
    ) -> tuple[list[SupportMessage], int]:
        filters = [SupportMessage.conversation_id == conversation_id]
        total = self._db.scalar(select(func.count(SupportMessage.id)).where(*filters)) or 0
        offset = (page - 1) * limit
        items = list(
            self._db.scalars(
                select(SupportMessage)
                .where(*filters)
                .order_by(SupportMessage.created_at.asc())
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, total
