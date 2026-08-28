from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field  # pyright: ignore[reportMissingImports]

from app.schemas.pagination import PaginatedResponse


class ProductCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=150, examples=["iPhone 15"])
    description: str | None = Field(
        default=None,
        max_length=2000,
        examples=["Latest Apple smartphone"],
    )
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, examples=["999.99"])
    category_id: UUID = Field(
        ...,
        alias="categoryId",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class ProductUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=2, max_length=150, examples=["iPhone 15 Pro"])
    description: str | None = Field(
        default=None,
        max_length=2000,
        examples=["Pro model with better camera"],
    )
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, examples=["1199.99"])
    category_id: UUID = Field(
        ...,
        alias="categoryId",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    description: str | None = None
    price: Decimal
    category_id: UUID = Field(serialization_alias="categoryId")
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
