from uuid import UUID

from app.core.logging import get_logger
from app.core.tenant import get_current_organization_id
from app.models.notification import Notification, NotificationType
from app.models.order import Order, OrderStatus
from app.models.user import ORDER_ROLES, STOCK_ALERT_ROLES, User
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.notification import NotificationListResponse, NotificationRead, NotificationResponse
from app.services.notification_hub import notify_inbox

logger = get_logger(__name__)


class InboxNotificationService:
    def __init__(self, notifications: NotificationRepository, users: UserRepository) -> None:
        self._notifications = notifications
        self._users = users

    @classmethod
    def from_session(cls, db) -> "InboxNotificationService":
        return cls(NotificationRepository(db), UserRepository(db))

    def list_for(self, current_user: User) -> NotificationListResponse:
        rows = self._notifications.list_for_user(current_user.id)
        return NotificationListResponse(
            message="Notifications fetched",
            data=[NotificationRead.model_validate(row) for row in rows],
            unread_count=self._notifications.unread_count(current_user.id),
        )

    def mark_read(self, notification_id: UUID, *, current_user: User) -> NotificationResponse:
        from app.core.exceptions import NotFoundError

        row = self._notifications.get_for_user(notification_id, current_user.id)
        if row is None:
            raise NotFoundError("Notification not found")
        updated = self._notifications.mark_read(row)
        return NotificationResponse(
            message="Notification marked as read",
            notification=NotificationRead.model_validate(updated),
        )

    def mark_all_read(self, *, current_user: User):
        from app.schemas.common import MessageResponse

        self._notifications.mark_all_read(current_user.id)
        return MessageResponse(message="All notifications marked as read")

    def notify_order_paid(self, order: Order) -> None:
        number = f"#{order.order_number}"
        total = f"${order.total:.2f}"
        buyer = order.shipping_name or "A customer"
        self._create(
            user_id=order.user_id,
            organization_id=order.organization_id,
            title="Order placed successfully",
            description=f"Your order {number} has been placed for {total}",
            type=NotificationType.ORDER_PLACED,
            order_id=order.id,
        )
        for staff in self._staff(ORDER_ROLES, order.organization_id, exclude=order.user_id):
            self._create(
                user_id=staff.id,
                organization_id=order.organization_id,
                title="New order received",
                description=f"{buyer} placed order {number} for {total}",
                type=NotificationType.NEW_ORDER,
                order_id=order.id,
            )

    def notify_order_status(self, order: Order) -> None:
        number = f"#{order.order_number}"
        if order.status is OrderStatus.SHIPPED:
            title = "Your order has shipped"
            description = f"Order {number} is on the way"
            kind = NotificationType.ORDER_SHIPPED
        elif order.status is OrderStatus.DELIVERED:
            title = "Delivered — rate your products"
            description = f"Order {number} was delivered. Share a review to help other shoppers."
            kind = NotificationType.ORDER_DELIVERED
        elif order.status is OrderStatus.CANCELLED:
            title = "Order cancelled"
            description = f"Order {number} was cancelled"
            kind = NotificationType.ORDER_STATUS
        elif order.status is OrderStatus.RETURNED:
            title = "Return approved"
            description = f"Order {number} was refunded"
            kind = NotificationType.ORDER_STATUS
        else:
            title = "Order status updated"
            description = f"Order {number} is now {order.status.value.lower()}"
            kind = NotificationType.ORDER_STATUS
        self._create(
            user_id=order.user_id,
            organization_id=order.organization_id,
            title=title,
            description=description,
            type=kind,
            order_id=order.id,
        )

    def notify_return_rejected(self, order: Order) -> None:
        self._create(
            user_id=order.user_id,
            organization_id=order.organization_id,
            title="Return request not approved",
            description=f"We could not approve a return on order #{order.order_number}",
            type=NotificationType.ORDER_STATUS,
            order_id=order.id,
        )

    def notify_return_request(self, order: Order) -> None:
        buyer = order.shipping_name or "Customer"
        for staff in self._staff(ORDER_ROLES, order.organization_id, exclude=order.user_id):
            self._create(
                user_id=staff.id,
                organization_id=order.organization_id,
                title="Return / refund requested",
                description=f"{buyer} requested a return on order #{order.order_number}",
                type=NotificationType.RETURN_REQUEST,
                order_id=order.id,
            )

    def notify_low_stock(
        self,
        *,
        organization_id: UUID | None,
        product_id: UUID,
        product_name: str,
        stock: int,
        threshold: int,
    ) -> None:
        org_id = organization_id or get_current_organization_id(self._notifications._db)
        if org_id is None:
            return
        stock_label = "out of stock" if stock <= 0 else f"{stock} left"
        for staff in self._staff(STOCK_ALERT_ROLES, org_id):
            self._create(
                user_id=staff.id,
                organization_id=org_id,
                title=f"Low stock: {product_name}",
                description=f"{product_name} is {stock_label} (threshold {threshold}).",
                type=NotificationType.LOW_STOCK,
                product_id=product_id,
            )

    def notify_support_message(
        self,
        *,
        recipient_ids: set[UUID],
        sender_id: UUID,
        organization_id: UUID | None,
        conversation_id: UUID,
        title: str,
        description: str,
    ) -> None:
        org_id = organization_id or get_current_organization_id(self._notifications._db)
        if org_id is None:
            return
        for user_id in recipient_ids:
            if user_id == sender_id:
                continue
            self._create(
                user_id=user_id,
                organization_id=org_id,
                title=title,
                description=description,
                type=NotificationType.SUPPORT_MESSAGE,
                conversation_id=conversation_id,
            )

    def _staff(self, roles: set, organization_id: UUID, exclude: UUID | None = None) -> list[User]:
        rows = self._users.list_by_roles(roles, organization_id=organization_id)
        if exclude is None:
            return rows
        return [row for row in rows if row.id != exclude]

    def _create(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        title: str,
        description: str,
        type: NotificationType,
        order_id: UUID | None = None,
        product_id: UUID | None = None,
        conversation_id: UUID | None = None,
    ) -> Notification:
        existing = self._notifications.find_open_duplicate(
            user_id=user_id,
            type=type.value,
            order_id=order_id,
            product_id=product_id,
        )
        if existing is not None and conversation_id is None:
            return existing
        row = self._notifications.create(
            user_id=user_id,
            organization_id=organization_id,
            title=title,
            description=description,
            type=type.value,
            order_id=order_id,
            product_id=product_id,
            conversation_id=conversation_id,
        )
        notify_inbox(
            user_id=user_id,
            payload={
                "type": "inbox.notification",
                "notification": NotificationRead.model_validate(row).model_dump(by_alias=True, mode="json"),
            },
        )
        return row
