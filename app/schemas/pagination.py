import math
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationQuery(BaseModel):
    """Common query params for list endpoints (like NestJS PaginationDto)."""

    page: int = Field(default=1, ge=1, examples=[1])
    limit: int = Field(default=10, ge=1, le=100, examples=[10])
    search: str | None = Field(default=None, max_length=100, examples=["Electronics"])


class PaginationMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int = Field(examples=[25])
    page: int = Field(examples=[1])
    limit: int = Field(examples=[10])
    total_pages: int = Field(serialization_alias="totalPages", examples=[3])
    has_next_page: bool = Field(serialization_alias="hasNextPage", examples=[True])
    has_previous_page: bool = Field(
        serialization_alias="hasPreviousPage",
        examples=[False],
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Reusable paginated list response for any resource."""

    message: str
    data: list[T]
    meta: PaginationMeta


def build_pagination_meta(*, total: int, page: int, limit: int) -> PaginationMeta:
    total_pages = math.ceil(total / limit) if total > 0 else 0
    return PaginationMeta(
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        has_next_page=page < total_pages,
        has_previous_page=page > 1 and total_pages > 0,
    )
