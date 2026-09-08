from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductRead


class WishlistAddRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: UUID = Field(..., alias="productId")


class WishlistIdsResponse(BaseModel):
    message: str
    ids: list[UUID]


class WishlistListResponse(BaseModel):
    message: str
    data: list[ProductRead]
    ids: list[UUID]


class WishlistItemResponse(BaseModel):
    message: str
    product: ProductRead
    ids: list[UUID]
