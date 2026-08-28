from decimal import Decimal
from uuid import UUID

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.logging import get_logger
from app.models.cart import CartItem
from app.models.user import User
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
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
        orders: OrderService,
    ) -> None:
        self._cart = cart
        self._products = products
        self._orders = orders

    def get_cart(self, current_user: User) -> CartResponse:
        items = self._cart.list_by_user(current_user.id)
        return self._build_cart_response("Cart fetched successfully", items)

    def add_item(self, payload: CartItemAddRequest, *, current_user: User) -> CartResponse:
        self._ensure_active_product(payload.product_id)
        self._cart.add_item(
            user_id=current_user.id,
            product_id=payload.product_id,
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
        item = self._get_cart_item(current_user.id, product_id)
        self._cart.set_quantity(item, quantity=payload.quantity)
        items = self._cart.list_by_user(current_user.id)
        return self._build_cart_response("Cart item updated", items)

    def remove_item(self, product_id: UUID, *, current_user: User) -> CartResponse:
        item = self._get_cart_item(current_user.id, product_id)
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
                OrderItemCreateRequest(productId=item.product_id, quantity=item.quantity)
                for item in items
            ],
            paymentMethodId=payload.payment_method_id,
        )
        order_response = self._orders.create_order(order_payload, current_user=current_user)
        self._cart.clear(current_user.id)
        logger.info("Checked out cart for user %s into order", current_user.id)

        return CartCheckoutResponse(
            message="Order created from cart successfully",
            order=order_response.order,
        )

    def _get_cart_item(self, user_id: UUID, product_id: UUID) -> CartItem:
        item = self._cart.get_item(user_id, product_id)
        if item is None:
            raise NotFoundError("Cart item not found")
        return item

    def _ensure_active_product(self, product_id: UUID) -> None:
        if self._products.get_by_id(product_id) is None:
            raise NotFoundError("Product not found")

    def _build_cart_response(self, message: str, items: list[CartItem]) -> CartResponse:
        cart_items = [self._to_cart_item_read(item) for item in items]
        total = sum((item.subtotal for item in cart_items), Decimal("0.00"))
        return CartResponse(message=message, items=cart_items, total=total)

    def _to_cart_item_read(self, item: CartItem) -> CartItemRead:
        subtotal = Decimal(item.product.price) * item.quantity
        return CartItemRead(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price=Decimal(item.product.price),
            subtotal=subtotal,
        )
