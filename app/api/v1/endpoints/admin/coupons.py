from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentCatalogStaffDep, CouponServiceDep
from app.schemas.common import MessageResponse
from app.schemas.coupon import (
    CouponCreateRequest,
    CouponListResponse,
    CouponPreviewResponse,
    CouponResponse,
    CouponUpdateRequest,
)

router = APIRouter(prefix="/coupons", tags=["Admin — Coupons"])


@router.get("", response_model=CouponListResponse)
def list_coupons(_: CurrentCatalogStaffDep, coupons: CouponServiceDep):
    return coupons.list_coupons()


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(payload: CouponCreateRequest, _: CurrentCatalogStaffDep, coupons: CouponServiceDep):
    return coupons.create_coupon(payload)


@router.patch("/{coupon_id}", response_model=CouponResponse)
def update_coupon(
    coupon_id: UUID,
    payload: CouponUpdateRequest,
    _: CurrentCatalogStaffDep,
    coupons: CouponServiceDep,
):
    return coupons.update_coupon(coupon_id, payload)


@router.delete("/{coupon_id}", response_model=MessageResponse)
def delete_coupon(coupon_id: UUID, _: CurrentCatalogStaffDep, coupons: CouponServiceDep):
    return coupons.delete_coupon(coupon_id)


@router.get("/preview", response_model=CouponPreviewResponse)
def preview_coupon(
    code: str,
    _: CurrentCatalogStaffDep,
    coupons: CouponServiceDep,
    subtotal: Decimal = Query(default=Decimal("0"), ge=0),
):
    return coupons.preview(code, subtotal=subtotal)
