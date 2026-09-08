from datetime import datetime
from uuid import UUID

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.order import OrderStatus
from app.models.support import SupportConversation, SupportMessage
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.support_repository import SupportRepository
from app.repositories.user_repository import UserRepository
from app.schemas.pagination import PaginationQuery, build_pagination_meta
from app.schemas.support import (
    SupportChannel,
    SupportColleagueListResponse,
    SupportColleagueRead,
    SupportContextType,
    SupportConversationCreateRequest,
    SupportConversationListResponse,
    SupportConversationRead,
    SupportConversationResponse,
    SupportConversationStatus,
    SupportMessageCreateRequest,
    SupportMessageListResponse,
    SupportMessageRead,
    SupportMessageResponse,
    SupportPresenceResponse,
    SupportStaffConversationCreateRequest,
    SupportUnreadResponse,
)
from app.services.audit_service import AuditService
from app.services.notification_hub import hub, notify_support_assigned, notify_support_message, notify_support_seen


class SupportService:
    def __init__(
        self,
        conversations: SupportRepository,
        orders: OrderRepository,
        products: ProductRepository,
        users: UserRepository,
        audit: AuditService | None = None,
    ) -> None:
        self._conversations = conversations
        self._orders = orders
        self._products = products
        self._users = users
        self._audit = audit

    def list_conversations(
        self,
        pagination: PaginationQuery,
        *,
        current_user: User,
        status: SupportConversationStatus | None = None,
        context_type: SupportContextType | None = None,
        channel: SupportChannel = SupportChannel.CUSTOMER,
        assigned_to_me: bool = False,
        unassigned: bool = False,
    ) -> SupportConversationListResponse:
        if channel is SupportChannel.STAFF:
            if not current_user.is_staff:
                raise ForbiddenError("Staff access required")
            items, total = self._conversations.list_conversations(
                page=pagination.page,
                limit=pagination.limit,
                status=status,
                context_type=context_type,
                search=pagination.search,
                channel=SupportChannel.STAFF,
                participant_id=current_user.id,
            )
            unread_map = self._conversations.unread_message_counts(
                [item.id for item in items],
                reader_is_staff=True,
                reader_id=current_user.id,
                channel=SupportChannel.STAFF,
            )
        else:
            is_staff = current_user.can_manage_support
            items, total = self._conversations.list_conversations(
                page=pagination.page,
                limit=pagination.limit,
                user_id=None if is_staff else current_user.id,
                status=status,
                context_type=context_type,
                search=pagination.search,
                channel=SupportChannel.CUSTOMER,
                assigned_to_id=current_user.id if is_staff and assigned_to_me else None,
                unassigned=bool(is_staff and unassigned),
            )
            unread_map = self._conversations.unread_message_counts(
                [item.id for item in items],
                reader_is_staff=is_staff,
            )
        return SupportConversationListResponse(
            message="Support conversations fetched",
            data=[
                self._to_conversation(item, viewer=current_user, unread=unread_map.get(item.id, 0))
                for item in items
            ],
            meta=build_pagination_meta(total=total, page=pagination.page, limit=pagination.limit),
        )

    def unread_count(
        self,
        *,
        current_user: User,
        channel: SupportChannel | None = None,
    ) -> SupportUnreadResponse:
        customer = self._conversations.unread_count(
            user_id=current_user.id,
            is_staff=current_user.can_manage_support,
        )
        team = self._conversations.unread_staff_count(user_id=current_user.id) if current_user.is_staff else 0
        if channel is SupportChannel.STAFF:
            if not current_user.is_staff:
                raise ForbiddenError("Staff access required")
            count = team
        elif channel is SupportChannel.CUSTOMER:
            count = customer
        else:
            count = customer + team if current_user.is_staff else customer
        return SupportUnreadResponse(message="Unread support count fetched", count=count)

    def list_colleagues(self, *, current_user: User) -> SupportColleagueListResponse:
        if not current_user.is_staff:
            raise ForbiddenError("Staff access required")
        return SupportColleagueListResponse(
            message="Staff colleagues fetched",
            data=[
                SupportColleagueRead.model_validate(user)
                for user in self._users.list_staff(exclude_id=current_user.id)
            ],
        )

    def presence(self) -> SupportPresenceResponse:
        return SupportPresenceResponse(
            message="Support presence fetched",
            support_online=hub.support_online,
            online_user_ids=[str(user_id) for user_id in hub.online_ids],
        )

    def get_conversation(self, conversation_id: UUID, *, current_user: User) -> SupportConversationResponse:
        conversation = self._require_conversation(conversation_id, current_user)
        self._acknowledge(conversation, current_user)
        return SupportConversationResponse(
            message="Support conversation fetched",
            conversation=self._to_conversation(conversation, viewer=current_user),
        )

    def mark_seen(self, conversation_id: UUID, *, current_user: User) -> SupportConversationResponse:
        conversation = self._require_conversation(conversation_id, current_user)
        self._acknowledge(conversation, current_user)
        return SupportConversationResponse(
            message="Conversation marked seen",
            conversation=self._to_conversation(conversation, viewer=current_user),
        )

    def start_conversation(
        self,
        payload: SupportConversationCreateRequest,
        *,
        current_user: User,
    ) -> SupportConversationResponse:
        if current_user.can_manage_support:
            raise BadRequestError("Support staff reply in existing conversations")
        order_id = None
        product_id = None
        subject = (payload.subject or "").strip()
        if payload.context_type == SupportContextType.ORDER:
            if payload.order_id is None:
                raise BadRequestError("Order is required for order support")
            order = self._orders.get_by_id(payload.order_id)
            if order is None:
                raise NotFoundError("Order not found")
            if order.user_id != current_user.id:
                raise ForbiddenError("You can only ask about your own orders")
            order_id = order.id
            subject = subject or f"Order #{order.order_number}"
            if order.status in {OrderStatus.DELIVERED, OrderStatus.RETURNED}:
                existing = self._conversations.find_for_context(
                    user_id=current_user.id,
                    context_type=payload.context_type,
                    order_id=order_id,
                )
                if existing is None:
                    raise BadRequestError("This order was marked as received, so order support chat is closed")
        elif payload.context_type == SupportContextType.PRODUCT:
            if payload.product_id is None:
                raise BadRequestError("Product is required for product support")
            product = self._products.get_by_id(payload.product_id)
            if product is None or product.deleted_at is not None:
                raise NotFoundError("Product not found")
            product_id = product.id
            subject = subject or product.name
        else:
            if payload.order_id or payload.product_id:
                raise BadRequestError("General support cannot include an order or product")
            subject = subject or "Support request"

        conversation = self._conversations.find_for_context(
            user_id=current_user.id,
            context_type=payload.context_type,
            order_id=order_id,
            product_id=product_id,
        )
        if conversation is None:
            conversation = self._conversations.create_conversation(
                user_id=current_user.id,
                context_type=payload.context_type,
                subject=subject,
                order_id=order_id,
                product_id=product_id,
            )
        elif self._chat_closed(conversation):
            raise BadRequestError("This order was marked as received, so order support chat is closed")
        message = self._conversations.add_message(
            conversation,
            sender_id=current_user.id,
            body=payload.message.strip(),
            is_staff=False,
        )
        self._notify(conversation, message)
        return SupportConversationResponse(
            message="Support conversation started",
            conversation=self._to_conversation(conversation, viewer=current_user),
        )

    def start_staff_conversation(
        self,
        payload: SupportStaffConversationCreateRequest,
        *,
        current_user: User,
    ) -> SupportConversationResponse:
        if not current_user.is_staff:
            raise ForbiddenError("Staff access required")
        if payload.peer_id == current_user.id:
            raise BadRequestError("You cannot start a chat with yourself")
        peer = self._users.get_by_id(payload.peer_id)
        if peer is None or not peer.is_staff:
            raise NotFoundError("Staff member not found")
        left_id, right_id = _staff_pair(current_user.id, peer.id)
        conversation = self._conversations.find_staff_pair(left_id, right_id)
        if conversation is None:
            conversation = self._conversations.create_conversation(
                user_id=left_id,
                peer_id=right_id,
                channel=SupportChannel.STAFF,
                context_type=SupportContextType.GENERAL,
                subject="Team chat",
                order_id=None,
                product_id=None,
            )
        message = self._conversations.add_message(
            conversation,
            sender_id=current_user.id,
            body=payload.message.strip(),
            is_staff=True,
        )
        self._notify(conversation, message)
        return SupportConversationResponse(
            message="Team chat started",
            conversation=self._to_conversation(conversation, viewer=current_user),
        )

    def list_messages(
        self,
        conversation_id: UUID,
        pagination: PaginationQuery,
        *,
        current_user: User,
    ) -> SupportMessageListResponse:
        conversation = self._require_conversation(conversation_id, current_user)
        self._acknowledge(conversation, current_user)
        items, total = self._conversations.list_messages(
            conversation_id,
            page=pagination.page,
            limit=pagination.limit,
        )
        return SupportMessageListResponse(
            message="Support messages fetched",
            data=[self._to_message(item) for item in items],
            meta=build_pagination_meta(total=total, page=pagination.page, limit=pagination.limit),
            conversation=self._to_conversation(conversation, viewer=current_user),
        )

    def send_message(
        self,
        conversation_id: UUID,
        payload: SupportMessageCreateRequest,
        *,
        current_user: User,
    ) -> SupportMessageResponse:
        conversation = self._require_conversation(conversation_id, current_user)
        staff_channel = _is_staff_channel(conversation)
        is_staff = True if staff_channel else current_user.can_manage_support
        if self._chat_closed(conversation) and not is_staff:
            raise BadRequestError("This order was marked as received, so order support chat is closed")
        message = self._conversations.add_message(
            conversation,
            sender_id=current_user.id,
            body=payload.body.strip(),
            is_staff=is_staff,
        )
        self._notify(conversation, message)
        return SupportMessageResponse(message="Message sent", data=self._to_message(message))

    def set_status(
        self,
        conversation_id: UUID,
        status: SupportConversationStatus,
        *,
        current_user: User,
    ) -> SupportConversationResponse:
        if not current_user.can_manage_support:
            raise ForbiddenError("Only support staff can change conversation status")
        conversation = self._require_conversation(conversation_id, current_user)
        if _is_staff_channel(conversation):
            raise BadRequestError("Team chats stay open between staff")
        conversation = self._conversations.set_status(conversation, status)
        return SupportConversationResponse(
            message=f"Conversation {status.value.lower()}",
            conversation=self._to_conversation(conversation, viewer=current_user),
        )

    def assign_to_me(self, conversation_id: UUID, *, current_user: User) -> SupportConversationResponse:
        if not current_user.can_manage_support:
            raise ForbiddenError("Only support staff can claim a ticket")
        conversation = self._require_conversation(conversation_id, current_user)
        if _is_staff_channel(conversation):
            raise BadRequestError("Team chats are not assigned")
        previous = conversation.assigned_to
        conversation = self._conversations.set_assignee(conversation, user_id=current_user.id)
        if self._audit is not None:
            self._audit.record(
                actor=current_user,
                action="support.assigned",
                target_type="conversation",
                target_id=conversation.id,
                summary=f"Claimed support ticket “{conversation.subject}”",
                extra={
                    "previousAssigneeId": str(previous.id) if previous else None,
                    "previousAssigneeName": previous.name if previous else None,
                },
            )
        self._notify_assignment(conversation)
        return SupportConversationResponse(
            message="Ticket assigned to you",
            conversation=self._to_conversation(conversation, viewer=current_user),
        )

    def unassign(self, conversation_id: UUID, *, current_user: User) -> SupportConversationResponse:
        if not current_user.can_manage_support:
            raise ForbiddenError("Only support staff can release a ticket")
        conversation = self._require_conversation(conversation_id, current_user)
        if _is_staff_channel(conversation):
            raise BadRequestError("Team chats are not assigned")
        previous = conversation.assigned_to
        conversation = self._conversations.set_assignee(conversation, user_id=None)
        if self._audit is not None:
            self._audit.record(
                actor=current_user,
                action="support.unassigned",
                target_type="conversation",
                target_id=conversation.id,
                summary=f"Released support ticket “{conversation.subject}”",
                extra={
                    "previousAssigneeId": str(previous.id) if previous else None,
                    "previousAssigneeName": previous.name if previous else None,
                },
            )
        self._notify_assignment(conversation)
        return SupportConversationResponse(
            message="Ticket released",
            conversation=self._to_conversation(conversation, viewer=current_user),
        )

    def _notify_assignment(self, conversation: SupportConversation) -> None:
        notify_support_assigned(
            payload={
                "type": "support.assigned",
                "conversationId": str(conversation.id),
                "assignedToId": str(conversation.assigned_to_id) if conversation.assigned_to_id else None,
                "assignedToName": conversation.assigned_to.name if conversation.assigned_to else None,
            }
        )

    def _require_conversation(self, conversation_id: UUID, current_user: User) -> SupportConversation:
        conversation = self._conversations.get_conversation(conversation_id)
        if conversation is None:
            raise NotFoundError("Support conversation not found")
        if _is_staff_channel(conversation):
            if not current_user.is_staff or current_user.id not in {
                conversation.user_id,
                conversation.peer_id,
            }:
                raise ForbiddenError("You can only open your own team chats")
            return conversation
        if not current_user.can_manage_support and conversation.user_id != current_user.id:
            raise ForbiddenError("You can only open your own support conversations")
        return conversation

    def _notify(self, conversation: SupportConversation, message: SupportMessage) -> None:
        payload = {
            "type": "support.message",
            "conversationId": str(conversation.id),
            "contextType": conversation.context_type,
            "channel": conversation.channel,
            "subject": conversation.subject,
            "preview": conversation.last_message_preview,
            "message": {
                "id": str(message.id),
                "conversationId": str(conversation.id),
                "senderId": str(message.sender_id),
                "senderName": message.sender.name if message.sender else "Support",
                "senderRole": message.sender.role.value if message.sender else None,
                "isStaff": message.is_staff,
                "body": message.body,
                "createdAt": _iso(message.created_at),
                "seenAt": None,
            },
        }
        if _is_staff_channel(conversation):
            recipients = {conversation.user_id}
            if conversation.peer_id is not None:
                recipients.add(conversation.peer_id)
            notify_support_message(customer_id=conversation.user_id, payload=payload, recipients=recipients)
            return
        notify_support_message(customer_id=conversation.user_id, payload=payload)

    def _acknowledge(self, conversation: SupportConversation, current_user: User) -> None:
        staff_channel = _is_staff_channel(conversation)
        is_staff = True if staff_channel else current_user.can_manage_support
        self._conversations.mark_read(conversation, is_staff=is_staff)
        seen = self._conversations.mark_messages_seen(
            conversation.id,
            reader_is_staff=is_staff,
            reader_id=current_user.id,
            channel=SupportChannel.STAFF if staff_channel else SupportChannel.CUSTOMER,
        )
        if not seen:
            return
        seen_payload = {
            "type": "support.seen",
            "conversationId": str(conversation.id),
            "messageIds": [str(item.id) for item in seen],
            "seenAt": _iso(seen[0].seen_at) if seen[0].seen_at else None,
        }
        if staff_channel:
            recipients = {conversation.user_id}
            if conversation.peer_id is not None:
                recipients.add(conversation.peer_id)
            notify_support_seen(
                customer_id=conversation.user_id,
                payload=seen_payload,
                recipients=recipients,
            )
            return
        notify_support_seen(customer_id=conversation.user_id, payload=seen_payload)

    def _chat_closed(self, conversation: SupportConversation) -> bool:
        if conversation.context_type != SupportContextType.ORDER.value or conversation.order is None:
            return False
        return conversation.order.status in {OrderStatus.DELIVERED, OrderStatus.RETURNED}

    def _to_conversation(
        self,
        conversation: SupportConversation,
        *,
        viewer: User,
        unread: int | None = None,
    ) -> SupportConversationRead:
        is_staff = viewer.can_manage_support
        channel = SupportChannel(conversation.channel) if conversation.channel else SupportChannel.CUSTOMER
        staff_channel = channel == SupportChannel.STAFF
        if unread is None:
            unread = self._conversations.unread_message_counts(
                [conversation.id],
                reader_is_staff=True if staff_channel else is_staff,
                reader_id=viewer.id,
                channel=channel,
            ).get(conversation.id, 0)
        other = _other_staff(conversation, viewer) if staff_channel else conversation.user
        if staff_channel:
            peer_online = hub.is_online(other.id) if other else False
        else:
            peer_online = hub.support_online if not is_staff else hub.is_online(conversation.user_id)
        return SupportConversationRead(
            id=conversation.id,
            user_id=conversation.user_id,
            customer_name=(other.name if other else "Teammate") if staff_channel else (
                conversation.user.name if conversation.user else "Customer"
            ),
            customer_email=(other.email if other else None) if staff_channel else (
                conversation.user.email if conversation.user else None
            ),
            channel=channel,
            peer_id=other.id if staff_channel and other else conversation.peer_id,
            peer_name=other.name if staff_channel and other else None,
            peer_role=other.role if staff_channel and other else None,
            status=SupportConversationStatus(conversation.status),
            context_type=SupportContextType(conversation.context_type),
            order_id=conversation.order_id,
            order_number=conversation.order.order_number if conversation.order else None,
            product_id=conversation.product_id,
            product_name=conversation.product.name if conversation.product else None,
            subject=conversation.subject,
            last_message_preview=conversation.last_message_preview,
            last_message_at=conversation.last_message_at,
            last_sender_is_staff=conversation.last_sender_is_staff,
            unread_count=unread,
            peer_online=peer_online,
            chat_closed=self._chat_closed(conversation),
            assigned_to_id=conversation.assigned_to_id,
            assigned_to_name=conversation.assigned_to.name if conversation.assigned_to else None,
            assigned_to_role=conversation.assigned_to.role if conversation.assigned_to else None,
            assigned_at=conversation.assigned_at,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    def _to_message(self, message: SupportMessage) -> SupportMessageRead:
        return SupportMessageRead(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_name=message.sender.name if message.sender else "Support",
            sender_role=message.sender.role.value if message.sender else None,
            is_staff=message.is_staff,
            body=message.body,
            seen_at=message.seen_at,
            created_at=message.created_at,
        )


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.isoformat()


def _is_staff_channel(conversation: SupportConversation) -> bool:
    return conversation.channel == SupportChannel.STAFF.value


def _staff_pair(left: UUID, right: UUID) -> tuple[UUID, UUID]:
    return (left, right) if left.int < right.int else (right, left)


def _other_staff(conversation: SupportConversation, viewer: User):
    if conversation.user_id == viewer.id:
        return conversation.peer
    return conversation.user
