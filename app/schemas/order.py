from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus
from app.schemas.pagination import PaginatedResponse


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
        min_length=3,
        examples=["pm_1ExamplePaymentMethod"],
    )


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus = Field(examples=[OrderStatus.PAID])


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
    status: OrderStatus
    subtotal: Decimal
    stripe_fee: Decimal = Field(serialization_alias="stripeFee")
    total: Decimal
    item_count: int = Field(serialization_alias="itemCount")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    order_number: int = Field(serialization_alias="orderNumber")
    user_id: UUID = Field(serialization_alias="userId")
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
    items: list[OrderItemRead]
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class OrderListResponse(PaginatedResponse[OrderSummaryRead]):
    """Paginated orders list using the shared pagination response shape."""


class OrderResponse(BaseModel):
    message: str
    order: OrderRead
