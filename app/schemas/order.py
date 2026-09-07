from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus, ReturnStatus
from app.schemas.pagination import PaginatedResponse
from app.schemas.payment import PAYMENT_METHOD_ID_PATTERN
from app.schemas.shipping import ShippingAddressRead, ShippingAddressRequest


class OrderItemCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: UUID = Field(..., alias="productId")
    variant_id: UUID | None = Field(default=None, alias="variantId")
    quantity: int = Field(..., ge=1, examples=[2])


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[OrderItemCreateRequest] = Field(..., min_length=1)
    payment_method_id: str = Field(
        ...,
        alias="paymentMethodId",
        min_length=6,
        pattern=PAYMENT_METHOD_ID_PATTERN,
        examples=["pm_1ExamplePaymentMethod"],
    )
    shipping: ShippingAddressRequest


class OrderStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: OrderStatus = Field(examples=[OrderStatus.PROCESSING])
    tracking_number: str | None = Field(
        default=None,
        alias="trackingNumber",
        max_length=100,
    )


class ReturnRequestCreate(BaseModel):
    reason: str = Field(..., min_length=2, max_length=80)
    details: str | None = Field(default=None, max_length=500)


class ReturnReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    decision: ReturnStatus = Field(examples=[ReturnStatus.APPROVED])
    admin_note: str | None = Field(default=None, alias="adminNote", max_length=500)


class ReturnRequestRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: ReturnStatus
    reason: str | None = None
    details: str | None = None
    admin_note: str | None = Field(default=None, serialization_alias="adminNote")


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    product_id: UUID = Field(serialization_alias="productId")
    variant_id: UUID | None = Field(default=None, serialization_alias="variantId")
    product_name: str = Field(serialization_alias="productName")
    variant_name: str | None = Field(default=None, serialization_alias="variantName")
    quantity: int
    unit_price: Decimal = Field(serialization_alias="unitPrice")
    subtotal: Decimal


class OrderSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    order_number: int = Field(serialization_alias="orderNumber")
    user_id: UUID = Field(serialization_alias="userId")
    customer_name: str | None = Field(default=None, serialization_alias="customerName")
    customer_email: str | None = Field(default=None, serialization_alias="customerEmail")
    status: OrderStatus
    subtotal: Decimal
    stripe_fee: Decimal = Field(serialization_alias="stripeFee")
    total: Decimal
    item_count: int = Field(serialization_alias="itemCount")
    tracking_number: str | None = Field(default=None, serialization_alias="trackingNumber")
    amount_refunded: Decimal = Field(default=Decimal("0"), serialization_alias="amountRefunded")
    return_status: ReturnStatus | None = Field(default=None, serialization_alias="returnStatus")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    order_number: int = Field(serialization_alias="orderNumber")
    user_id: UUID = Field(serialization_alias="userId")
    customer_name: str | None = Field(default=None, serialization_alias="customerName")
    customer_email: str | None = Field(default=None, serialization_alias="customerEmail")
    status: OrderStatus
    subtotal: Decimal
    stripe_fee: Decimal = Field(serialization_alias="stripeFee")
    total: Decimal
    payment_method_id: str | None = Field(
        default=None,
        serialization_alias="paymentMethodId",
    )
    payment_intent_id: str | None = Field(
        default=None,
        serialization_alias="paymentIntentId",
    )
    tracking_number: str | None = Field(
        default=None,
        serialization_alias="trackingNumber",
    )
    amount_refunded: Decimal = Field(default=Decimal("0"), serialization_alias="amountRefunded")
    stripe_refund_id: str | None = Field(default=None, serialization_alias="stripeRefundId")
    delivered_at: datetime | None = Field(default=None, serialization_alias="deliveredAt")
    refunded_at: datetime | None = Field(default=None, serialization_alias="refundedAt")
    return_request: ReturnRequestRead | None = Field(default=None, serialization_alias="returnRequest")
    shipping: ShippingAddressRead | None = None
    items: list[OrderItemRead]
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class OrderListResponse(PaginatedResponse[OrderSummaryRead]):
    """Paginated orders list using the shared pagination response shape."""


class OrderResponse(BaseModel):
    message: str
    order: OrderRead
