from datetime import datetime, timezone
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.user import STOCK_ALERT_ROLES
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService
from app.services.inbox_notification_service import InboxNotificationService
from app.services.notification_hub import notify_low_stock

logger = get_logger(__name__)


class StockAlertService:
    def __init__(
        self,
        products: ProductRepository,
        users: UserRepository,
        emails: EmailService | None = None,
    ) -> None:
        self._products = products
        self._users = users
        self._emails = emails or EmailService()

    def check_product(self, product_id: UUID) -> None:
        try:
            self._check_product(product_id)
        except Exception:
            logger.exception("Low-stock alert failed for product %s", product_id)

    def check_products(self, product_ids: list[UUID]) -> None:
        seen: set[UUID] = set()
        for product_id in product_ids:
            if product_id in seen:
                continue
            seen.add(product_id)
            self.check_product(product_id)

    def _check_product(self, product_id: UUID) -> None:
        product = self._products.get_by_id(product_id)
        if product is None:
            return
        threshold = get_settings().LOW_STOCK_THRESHOLD
        if product.stock > threshold:
            if product.low_stock_alerted_at is not None:
                self._products.set_low_stock_alerted_at(product, None)
            return
        if product.low_stock_alerted_at is not None:
            return

        recipients = self._users.list_by_roles(
            STOCK_ALERT_ROLES,
            organization_id=getattr(product, "organization_id", None),
        )
        if not recipients:
            self._products.set_low_stock_alerted_at(product, datetime.now(timezone.utc))
            return

        stock_label = "out of stock" if product.stock <= 0 else f"{product.stock} left"
        subject = f"Low stock: {product.name}"
        intro = (
            f"{product.name} is {stock_label} (threshold {threshold}). "
            "Restock before the next orders come in."
        )
        for user in recipients:
            self._emails.send_staff_notice(
                to_email=user.email,
                subject=subject,
                headline="Low stock alert",
                intro=intro,
            )
        notify_low_stock(
            user_ids={user.id for user in recipients},
            product_id=product.id,
            product_name=product.name,
            stock=product.stock,
            threshold=threshold,
        )
        InboxNotificationService.from_session(self._products._db).notify_low_stock(
            organization_id=getattr(product, "organization_id", None),
            product_id=product.id,
            product_name=product.name,
            stock=product.stock,
            threshold=threshold,
        )
        self._products.set_low_stock_alerted_at(product, datetime.now(timezone.utc))
