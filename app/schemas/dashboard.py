from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LowStockItemRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    stock: int
    threshold: int
    is_out_of_stock: bool = Field(serialization_alias="isOutOfStock")
    image_url: str | None = Field(default=None, serialization_alias="imageUrl")


class LowStockListResponse(BaseModel):
    message: str
    threshold: int
    data: list[LowStockItemRead]
