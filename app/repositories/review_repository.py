from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.review import ProductReview


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_product(
        self,
        product_id: UUID,
        *,
        page: int,
        limit: int,
    ) -> tuple[list[ProductReview], int, float]:
        filters = [ProductReview.product_id == product_id]
        total = self._db.scalar(select(func.count(ProductReview.id)).where(*filters)) or 0
        avg = self._db.scalar(select(func.avg(ProductReview.rating)).where(*filters))
        offset = (page - 1) * limit
        items = list(
            self._db.scalars(
                select(ProductReview)
                .where(*filters)
                .order_by(ProductReview.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, total, float(avg or 0)

    def get_by_id(self, review_id: UUID) -> ProductReview | None:
        return self._db.scalar(select(ProductReview).where(ProductReview.id == review_id))

    def get_by_user_product(self, *, user_id: UUID, product_id: UUID) -> ProductReview | None:
        return self._db.scalar(
            select(ProductReview).where(
                ProductReview.user_id == user_id,
                ProductReview.product_id == product_id,
            )
        )

    def create(
        self,
        *,
        product_id: UUID,
        user_id: UUID,
        order_id: UUID | None,
        rating: int,
        title: str | None,
        comment: str,
    ) -> ProductReview:
        review = ProductReview(
            product_id=product_id,
            user_id=user_id,
            order_id=order_id,
            rating=rating,
            title=title,
            comment=comment,
        )
        self._db.add(review)
        self._db.commit()
        self._db.refresh(review)
        return review

    def update(
        self,
        review: ProductReview,
        *,
        rating: int,
        title: str | None,
        comment: str,
        order_id: UUID | None,
    ) -> ProductReview:
        review.rating = rating
        review.title = title
        review.comment = comment
        if order_id is not None:
            review.order_id = order_id
        review.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(review)
        return review

    def delete(self, review: ProductReview) -> None:
        self._db.delete(review)
        self._db.commit()
