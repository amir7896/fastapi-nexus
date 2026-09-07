from decimal import Decimal
from uuid import UUID

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.logging import get_logger
from app.helpers.pricing import resolve_unit_price
from app.models.cart import CartItem
from app.models.user import User
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.product_variant_repository import ProductVariantRepository
from app.schemas.cart import (
    CartCheckoutRequest,
    CartCheckoutResponse,
    CartItemAddRequest,
    CartItemRead,
    CartItemUpdateRequest,
    CartResponse,
)
from app.schemas.order import OrderCreateRequest, OrderItemCreateRequest
from app.services.order_service import OrderService

logger = get_logger(__name__)


class CartService:
    def __init__(
        self,
        cart: CartRepository,
        products: ProductRepository,
        variants: ProductVariantRepository,
        orders: OrderService,
    ) -> None:
        self._cart = cart
        self._products = products
        self._variants = variants
        self._orders = orders

    def get_cart(self, current_user: User) -> CartResponse:
        items = self._cart.list_by_user(current_user.id)
        return self._build_cart_response("Cart fetched successfully", items)

    def add_item(self, payload: CartItemAddRequest, *, current_user: User) -> CartResponse:
        product, variant, unit_price, available, display_name = self._resolve_line(
            product_id=payload.product_id,
            variant_id=payload.variant_id,
        )
        existing = self._cart.get_item(
            current_user.id,
            payload.product_id,
            payload.variant_id,
        )
        requested_total = payload.quantity + (existing.quantity if existing else 0)
        self._ensure_enough_stock(display_name, available, requested_total)

        self._cart.add_item(
            user_id=current_user.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            quantity=payload.quantity,
        )
        items = self._cart.list_by_user(current_user.id)
        logger.info("Added product %s to cart for user %s", payload.product_id, current_user.id)
        return self._build_cart_response("Item added to cart", items)

    def update_item(
        self,
        product_id: UUID,
        payload: CartItemUpdateRequest,
        *,
        current_user: User,
    ) -> CartResponse:
        item = self._get_cart_item(current_user.id, product_id, payload.variant_id)
        _, _, _, available, display_name = self._resolve_line(
            product_id=product_id,
            variant_id=payload.variant_id if payload.variant_id is not None else item.variant_id,
        )
        self._ensure_enough_stock(display_name, available, payload.quantity)
        self._cart.set_quantity(item, quantity=payload.quantity)
        items = self._cart.list_by_user(current_user.id)
        return self._build_cart_response("Cart item updated", items)

    def remove_item(
        self,
        product_id: UUID,
        *,
        current_user: User,
        variant_id: UUID | None = None,
    ) -> CartResponse:
        item = self._get_cart_item(current_user.id, product_id, variant_id)
        self._cart.remove_item(item)
        items = self._cart.list_by_user(current_user.id)
        return self._build_cart_response("Cart item removed", items)

    def clear_cart(self, current_user: User) -> CartResponse:
        self._cart.clear(current_user.id)
        return CartResponse(message="Cart cleared", items=[], total=Decimal("0.00"))

    def checkout(
        self,
        payload: CartCheckoutRequest,
        *,
        current_user: User,
    ) -> CartCheckoutResponse:
        items = self._cart.list_by_user(current_user.id)
        if not items:
            raise BadRequestError("Cart is empty")

        order_payload = OrderCreateRequest(
            items=[
                OrderItemCreateRequest(
                    productId=item.product_id,
                    variantId=item.variant_id,
                    quantity=item.quantity,
                )
                for item in items
            ],
            paymentMethodId=payload.payment_method_id,
            shipping=payload.shipping,
        )
        order_response = self._orders.create_order(order_payload, current_user=current_user)
        self._cart.clear(current_user.id)
        logger.info("Checked out cart for user %s into order", current_user.id)

        return CartCheckoutResponse(
            message="Order created from cart successfully",
            order=order_response.order,
        )

    def _resolve_line(self, *, product_id: UUID, variant_id: UUID | None):
        product = self._products.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product not found")

        has_variants = bool(product.variants)
        if has_variants and variant_id is None:
            raise BadRequestError(f"variantId is required for product '{product.name}'")
        if not has_variants and variant_id is not None:
            raise BadRequestError(f"Product '{product.name}' has no variants")

        if variant_id is None:
            unit_price = resolve_unit_price(product)
            return product, None, unit_price, product.stock, product.name

        variant = self._variants.get_by_id(variant_id)
        if variant is None or variant.product_id != product.id:
            raise NotFoundError("Variant not found")

        unit_price = resolve_unit_price(product, variant)
        display_name = f"{product.name} ({variant.name})" if variant.name else product.name
        return product, variant, unit_price, variant.stock, display_name

    def _get_cart_item(
        self,
        user_id: UUID,
        product_id: UUID,
        variant_id: UUID | None,
    ) -> CartItem:
        item = self._cart.get_item(user_id, product_id, variant_id)
        if item is None:
            raise NotFoundError("Cart item not found")
        return item

    def _ensure_enough_stock(self, display_name: str, available: int, quantity: int) -> None:
        if available < quantity:
            raise BadRequestError(
                f"Insufficient stock for '{display_name}' "
                f"(available: {available}, requested: {quantity})"
            )

    def _build_cart_response(self, message: str, items: list[CartItem]) -> CartResponse:
        cart_items = [self._to_cart_item_read(item) for item in items]
        total = sum((item.subtotal for item in cart_items), Decimal("0.00"))
        return CartResponse(message=message, items=cart_items, total=total)

    def _to_cart_item_read(self, item: CartItem) -> CartItemRead:
        variant = item.variant if item.variant_id else None
        unit_price = resolve_unit_price(item.product, variant)
        if variant is not None:
            variant_name = variant.name or None
            product_name = (
                f"{item.product.name} ({variant.name})"
                if variant.name
                else item.product.name
            )
        else:
            variant_name = None
            product_name = item.product.name

        image_url = (variant.image_url if variant and variant.image_url else None) or item.product.image_url

        return CartItemRead(
            id=item.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            product_name=product_name,
            variant_name=variant_name,
            image_url=image_url,
            quantity=item.quantity,
            unit_price=unit_price,
            subtotal=unit_price * item.quantity,
        )
