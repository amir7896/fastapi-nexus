from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PaginatedResponse


class ReviewCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rating: int = Field(..., ge=1, le=5, examples=[5])
    title: str | None = Field(default=None, max_length=120)
    comment: str = Field(..., min_length=2, max_length=2000)
    order_id: UUID | None = Field(default=None, alias="orderId")


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    product_id: UUID = Field(serialization_alias="productId")
    user_id: UUID = Field(serialization_alias="userId")
    order_id: UUID | None = Field(default=None, serialization_alias="orderId")
    user_name: str = Field(serialization_alias="userName")
    rating: int
    title: str | None = None
    comment: str
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class ReviewResponse(BaseModel):
    message: str
    review: ReviewRead


class ReviewListResponse(PaginatedResponse[ReviewRead]):
    average_rating: float = Field(serialization_alias="averageRating")
    review_count: int = Field(serialization_alias="reviewCount")


class ReviewEligibilityRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    can_review: bool = Field(serialization_alias="canReview")
    reason: str
    review: ReviewRead | None = None


class ReviewEligibilityResponse(BaseModel):
    message: str
    eligibility: ReviewEligibilityRead


class OrderReviewTargetRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: UUID = Field(serialization_alias="productId")
    product_name: str = Field(serialization_alias="productName")
    can_review: bool = Field(serialization_alias="canReview")
    review: ReviewRead | None = None


class OrderReviewTargetsResponse(BaseModel):
    message: str
    data: list[OrderReviewTargetRead]
