from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.order import OrderRead


class CartItemAddRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: UUID = Field(..., alias="productId")
    quantity: int = Field(..., ge=1, examples=[1])


class CartItemUpdateRequest(BaseModel):
    quantity: int = Field(..., ge=1, examples=[2])


class CartItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    product_id: UUID = Field(serialization_alias="productId")
    product_name: str = Field(serialization_alias="productName")
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
        min_length=3,
        examples=["pm_1ExamplePaymentMethod"],
    )


class CartCheckoutResponse(BaseModel):
    message: str
    order: OrderRead
