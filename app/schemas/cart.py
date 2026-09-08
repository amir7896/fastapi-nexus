from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order import OrderRead
from app.schemas.shipping import ShippingAddressRequest
from app.schemas.payment import PAYMENT_METHOD_ID_PATTERN


class CartItemAddRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: UUID = Field(..., alias="productId")
    variant_id: UUID | None = Field(default=None, alias="variantId")
    quantity: int = Field(..., ge=1, examples=[1])


class CartItemUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    quantity: int = Field(..., ge=1, examples=[2])
    variant_id: UUID | None = Field(default=None, alias="variantId")


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    product_id: UUID = Field(serialization_alias="productId")
    variant_id: UUID | None = Field(default=None, serialization_alias="variantId")
    product_name: str = Field(serialization_alias="productName")
    variant_name: str | None = Field(default=None, serialization_alias="variantName")
    image_url: str | None = Field(default=None, serialization_alias="imageUrl")
    quantity: int
    unit_price: Decimal = Field(serialization_alias="unitPrice")
    subtotal: Decimal


class CartResponse(BaseModel):
    message: str
    items: list[CartItemRead]
    total: Decimal


class CartCheckoutRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    payment_method_id: str = Field(
        ...,
        alias="paymentMethodId",
        min_length=6,
        pattern=PAYMENT_METHOD_ID_PATTERN,
        examples=["pm_1ExamplePaymentMethod"],
    )
    shipping: ShippingAddressRequest
    coupon_code: str | None = Field(default=None, alias="couponCode", max_length=40)


class CartCheckoutResponse(BaseModel):
    message: str
    order: OrderRead


class ReorderSkippedItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: UUID = Field(serialization_alias="productId")
    variant_id: UUID | None = Field(default=None, serialization_alias="variantId")
    product_name: str = Field(serialization_alias="productName")
    reason: str


class ReorderResponse(BaseModel):
    message: str
    cart: CartResponse
    skipped: list[ReorderSkippedItem]
