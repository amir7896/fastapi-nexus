from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.pagination import PaginatedResponse

ProductStatus = Literal["", "new", "sale"]
ProductSort = Literal["newest", "priceAsc", "priceDesc", "nameAsc"]


class ProductVariantCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=150, examples=["Black / M"])
    sku: str | None = Field(default=None, max_length=100, examples=["IPH15-BLK-M"])
    color: str | None = Field(default=None, max_length=50, examples=["Black"])
    size: str | None = Field(default=None, max_length=50, examples=["M"])
    material: str | None = Field(default=None, max_length=50)
    style: str | None = Field(default=None, max_length=50)
    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
        examples=["999.99"],
        description="Optional override; falls back to product price when null",
    )
    price_sale: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
        alias="priceSale",
        examples=["799.99"],
    )
    stock: int = Field(..., ge=0, examples=[10])


class ProductVariantUpdateRequest(ProductVariantCreateRequest):
    pass


class ProductVariantUpsertRequest(ProductVariantCreateRequest):
    """Used when replacing variants on product update; id keeps an existing row."""

    id: UUID | None = None


class ProductVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    product_id: UUID = Field(serialization_alias="productId")
    name: str
    sku: str | None = None
    color: str | None = None
    size: str | None = None
    material: str | None = None
    style: str | None = None
    price: Decimal | None = None
    price_sale: Decimal | None = Field(default=None, serialization_alias="priceSale")
    stock: int
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class ProductVariantResponse(BaseModel):
    message: str
    variant: ProductVariantRead


class ProductCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=150, examples=["iPhone 15"])
    description: str | None = Field(
        default=None,
        max_length=2000,
        examples=["Latest Apple smartphone"],
    )
    brand: str | None = Field(default=None, max_length=100, examples=["Apple"])
    sku: str | None = Field(default=None, max_length=100, examples=["IPH15"])
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, examples=["999.99"])
    price_sale: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
        alias="priceSale",
        examples=["899.99"],
    )
    colors: list[str] = Field(default_factory=list, examples=[["Black", "White"]])
    status: ProductStatus = Field(default="", examples=["sale"])
    stock: int = Field(
        default=0,
        ge=0,
        examples=[100],
        description="Used when variants is empty; ignored when variants are provided",
    )
    category_id: UUID = Field(
        ...,
        alias="categoryId",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    variants: list[ProductVariantCreateRequest] = Field(
        default_factory=list,
        examples=[
            [
                {
                    "name": "Black / M",
                    "sku": "IPH15-BLK-M",
                    "color": "Black",
                    "size": "M",
                    "stock": 10,
                },
                {
                    "name": "White / L",
                    "sku": "IPH15-WHT-L",
                    "color": "White",
                    "size": "L",
                    "price": "1099.99",
                    "stock": 5,
                },
            ]
        ],
    )

    @field_validator("colors", mode="before")
    @classmethod
    def _normalize_colors(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise ValueError("colors must be a list of strings")

    @model_validator(mode="after")
    def _validate_sale_price(self) -> "ProductCreateRequest":
        if self.price_sale is not None and self.price_sale >= self.price:
            raise ValueError("priceSale must be less than price")
        return self


class ProductUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=150, examples=["iPhone 15 Pro"])
    description: str | None = Field(
        default=None,
        max_length=2000,
        examples=["Pro model with better camera"],
    )
    brand: str | None = Field(default=None, max_length=100, examples=["Apple"])
    sku: str | None = Field(default=None, max_length=100, examples=["IPH15-PRO"])
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, examples=["1199.99"])
    price_sale: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
        alias="priceSale",
        examples=["999.99"],
    )
    colors: list[str] = Field(default_factory=list, examples=[["Black", "Blue"]])
    status: ProductStatus = Field(default="", examples=["new"])
    stock: int = Field(
        ...,
        ge=0,
        examples=[50],
        description="Used when product has no variants; ignored when variants are provided",
    )
    category_id: UUID = Field(
        ...,
        alias="categoryId",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    variants: list[ProductVariantUpsertRequest] | None = Field(
        default=None,
        description="When provided, replaces the full variant set (Dashboard-style)",
    )

    @field_validator("colors", mode="before")
    @classmethod
    def _normalize_colors(cls, value: object) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise ValueError("colors must be a list of strings")

    @model_validator(mode="after")
    def _validate_sale_price(self) -> "ProductUpdateRequest":
        if self.price_sale is not None and self.price_sale >= self.price:
            raise ValueError("priceSale must be less than price")
        return self


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    description: str | None = None
    brand: str | None = None
    sku: str | None = None
    price: Decimal
    price_sale: Decimal | None = Field(default=None, serialization_alias="priceSale")
    colors: list[str] = Field(default_factory=list)
    status: str = ""
    stock: int
    has_variants: bool = Field(default=False, serialization_alias="hasVariants")
    category_id: UUID = Field(serialization_alias="categoryId")
    variants: list[ProductVariantRead] = Field(default_factory=list)
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    deleted_at: datetime | None = Field(
        default=None,
        serialization_alias="deletedAt",
    )


class ProductListResponse(PaginatedResponse[ProductRead]):
    """Paginated products list using the shared pagination response shape."""


class ProductResponse(BaseModel):
    message: str
    product: ProductRead


class RelatedProductsResponse(BaseModel):
    message: str
    data: list[ProductRead]
