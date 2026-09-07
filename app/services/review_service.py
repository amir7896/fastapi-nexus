from uuid import UUID

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.order import OrderStatus
from app.models.review import ProductReview
from app.models.user import User, UserRole
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.pagination import PaginationQuery, build_pagination_meta
from app.schemas.review import (
    OrderReviewTargetRead,
    OrderReviewTargetsResponse,
    ReviewCreateRequest,
    ReviewEligibilityRead,
    ReviewEligibilityResponse,
    ReviewListResponse,
    ReviewRead,
    ReviewResponse,
)


class ReviewService:
    def __init__(
        self,
        reviews: ReviewRepository,
        orders: OrderRepository,
        products: ProductRepository,
    ) -> None:
        self._reviews = reviews
        self._orders = orders
        self._products = products

    def list_product_reviews(
        self,
        product_id: UUID,
        pagination: PaginationQuery,
    ) -> ReviewListResponse:
        self._require_product(product_id)
        items, total, average = self._reviews.list_by_product(
            product_id,
            page=pagination.page,
            limit=pagination.limit,
        )
        return ReviewListResponse(
            message="Reviews fetched successfully",
            data=[self._to_read(item) for item in items],
            meta=build_pagination_meta(total=total, page=pagination.page, limit=pagination.limit),
            average_rating=round(average, 1),
            review_count=total,
        )

    def get_eligibility(self, product_id: UUID, *, current_user: User | None) -> ReviewEligibilityResponse:
        self._require_product(product_id)
        if current_user is None:
            return ReviewEligibilityResponse(
                message="Review eligibility fetched",
                eligibility=ReviewEligibilityRead(can_review=False, reason="not_signed_in"),
            )
        existing = self._reviews.get_by_user_product(user_id=current_user.id, product_id=product_id)
        delivered = self._orders.get_delivered_for_product(
            user_id=current_user.id,
            product_id=product_id,
        )
        if delivered is None:
            reason = (
                "awaiting_delivery"
                if self._orders.has_purchase_of_product(user_id=current_user.id, product_id=product_id)
                else "not_purchased"
            )
            return ReviewEligibilityResponse(
                message="Review eligibility fetched",
                eligibility=ReviewEligibilityRead(
                    can_review=False,
                    reason=reason,
                    review=self._to_read(existing) if existing else None,
                ),
            )
        if existing is not None:
            return ReviewEligibilityResponse(
                message="Review eligibility fetched",
                eligibility=ReviewEligibilityRead(
                    can_review=True,
                    reason="already_reviewed",
                    review=self._to_read(existing),
                ),
            )
        return ReviewEligibilityResponse(
            message="Review eligibility fetched",
            eligibility=ReviewEligibilityRead(can_review=True, reason="eligible"),
        )

    def upsert_review(
        self,
        product_id: UUID,
        payload: ReviewCreateRequest,
        *,
        current_user: User,
    ) -> ReviewResponse:
        self._require_product(product_id)
        delivered = self._orders.get_delivered_for_product(
            user_id=current_user.id,
            product_id=product_id,
        )
        if delivered is None:
            raise BadRequestError("You can review a product after the order is delivered")
        title = (payload.title or "").strip() or None
        comment = payload.comment.strip()
        existing = self._reviews.get_by_user_product(user_id=current_user.id, product_id=product_id)
        if existing is None:
            review = self._reviews.create(
                product_id=product_id,
                user_id=current_user.id,
                order_id=payload.order_id or delivered.id,
                rating=payload.rating,
                title=title,
                comment=comment,
            )
            return ReviewResponse(message="Review submitted", review=self._to_read(review))
        review = self._reviews.update(
            existing,
            rating=payload.rating,
            title=title,
            comment=comment,
            order_id=payload.order_id or delivered.id,
        )
        return ReviewResponse(message="Review updated", review=self._to_read(review))

    def list_order_targets(self, order_id: UUID, *, current_user: User) -> OrderReviewTargetsResponse:
        order = self._orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if current_user.role is not UserRole.ADMIN and order.user_id != current_user.id:
            raise ForbiddenError("You can only review your own orders")
        if order.status is not OrderStatus.DELIVERED:
            return OrderReviewTargetsResponse(message="Reviews unlock after delivery", data=[])

        seen: set[UUID] = set()
        targets: list[OrderReviewTargetRead] = []
        for item in order.items:
            if item.product_id in seen:
                continue
            seen.add(item.product_id)
            existing = self._reviews.get_by_user_product(
                user_id=order.user_id,
                product_id=item.product_id,
            )
            name = item.product.name if item.product else "Product"
            targets.append(
                OrderReviewTargetRead(
                    product_id=item.product_id,
                    product_name=name,
                    can_review=True,
                    review=self._to_read(existing) if existing else None,
                )
            )
        return OrderReviewTargetsResponse(message="Review targets fetched", data=targets)

    def delete_review(self, review_id: UUID, *, current_user: User) -> ReviewResponse:
        review = self._reviews.get_by_id(review_id)
        if review is None:
            raise NotFoundError("Review not found")
        if current_user.role is not UserRole.ADMIN and review.user_id != current_user.id:
            raise ForbiddenError("You can only delete your own review")
        payload = self._to_read(review)
        self._reviews.delete(review)
        return ReviewResponse(message="Review deleted", review=payload)

    def _require_product(self, product_id: UUID) -> None:
        if self._products.get_by_id(product_id) is None:
            raise NotFoundError("Product not found")

    def _to_read(self, review: ProductReview) -> ReviewRead:
        return ReviewRead(
            id=review.id,
            product_id=review.product_id,
            user_id=review.user_id,
            order_id=review.order_id,
            user_name=review.user.name if review.user else "Customer",
            rating=review.rating,
            title=review.title,
            comment=review.comment,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
