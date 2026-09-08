from decimal import Decimal
from uuid import UUID

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.tenant import require_organization_id
from app.models.coupon import Coupon, CouponType
from app.repositories.coupon_repository import CouponRepository
from app.schemas.common import MessageResponse
from app.schemas.coupon import (
    CouponCreateRequest,
    CouponListResponse,
    CouponPreviewResponse,
    CouponRead,
    CouponResponse,
    CouponUpdateRequest,
)


class CouponService:
    def __init__(self, coupons: CouponRepository) -> None:
        self._coupons = coupons

    def list_coupons(self) -> CouponListResponse:
        require_organization_id(self._coupons._db)
        return CouponListResponse(
            message="Coupons fetched",
            data=[CouponRead.model_validate(row) for row in self._coupons.list_all()],
        )

    def create_coupon(self, payload: CouponCreateRequest) -> CouponResponse:
        code = payload.code.strip().upper()
        if self._coupons.get_by_code(code) is not None:
            raise ConflictError("That coupon code already exists")
        self._validate(payload.type, payload.value)
        row = self._coupons.create(
            code=code,
            type=payload.type.value,
            value=payload.value,
            min_subtotal=payload.min_subtotal,
            max_uses=payload.max_uses,
            used_count=0,
            is_active=payload.is_active,
            expires_at=payload.expires_at,
        )
        return CouponResponse(message="Coupon created", coupon=CouponRead.model_validate(row))

    def update_coupon(self, coupon_id: UUID, payload: CouponUpdateRequest) -> CouponResponse:
        row = self._require(coupon_id)
        if payload.type is not None:
            row.type = payload.type.value
        if payload.value is not None:
            row.value = payload.value
        self._validate(CouponType(row.type), row.value)
        if payload.min_subtotal is not None:
            row.min_subtotal = payload.min_subtotal
        if payload.max_uses is not None:
            row.max_uses = payload.max_uses
        if payload.expires_at is not None:
            row.expires_at = payload.expires_at
        if payload.is_active is not None:
            row.is_active = payload.is_active
        saved = self._coupons.save(row)
        return CouponResponse(message="Coupon updated", coupon=CouponRead.model_validate(saved))

    def delete_coupon(self, coupon_id: UUID) -> MessageResponse:
        self._coupons.delete(self._require(coupon_id))
        return MessageResponse(message="Coupon deleted")

    def preview(self, code: str, *, subtotal: Decimal) -> CouponPreviewResponse:
        row = self.apply(code, subtotal=subtotal, consume=False)
        return CouponPreviewResponse(
            message="Coupon is valid",
            code=row.code,
            type=row.type,
            value=row.value,
            discount=self.discount_for(row, subtotal),
            min_subtotal=row.min_subtotal,
        )

    def apply(self, code: str, *, subtotal: Decimal, consume: bool = False) -> Coupon:
        row = self._coupons.get_by_code(code)
        if row is None or not self._coupons.is_usable(row):
            raise BadRequestError("This coupon is not valid")
        if row.min_subtotal is not None and subtotal < row.min_subtotal:
            raise BadRequestError(f"Add ${row.min_subtotal:.2f} to use this coupon")
        if consume:
            self._coupons.increment_used(row)
        return row

    def discount_for(self, row: Coupon, subtotal: Decimal) -> Decimal:
        if row.type == CouponType.PERCENT.value:
            amount = (subtotal * row.value / Decimal("100")).quantize(Decimal("0.01"))
        else:
            amount = Decimal(row.value).quantize(Decimal("0.01"))
        if amount > subtotal:
            return subtotal
        return amount

    def _require(self, coupon_id: UUID) -> Coupon:
        row = self._coupons.get_by_id(coupon_id)
        if row is None:
            raise NotFoundError("Coupon not found")
        return row

    def _validate(self, kind: CouponType, value: Decimal) -> None:
        if kind is CouponType.PERCENT and value > 100:
            raise BadRequestError("Percent coupons cannot exceed 100")
