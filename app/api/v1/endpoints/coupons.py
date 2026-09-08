from decimal import Decimal

from fastapi import APIRouter, Query

from app.api.deps import CatalogViewerDep, CouponServiceDep
from app.schemas.coupon import CouponPreviewResponse

router = APIRouter(prefix="/coupons", tags=["Coupons"])


@router.get("/preview", response_model=CouponPreviewResponse)
def preview_coupon(
    code: str,
    _: CatalogViewerDep,
    coupons: CouponServiceDep,
    subtotal: Decimal = Query(default=Decimal("0"), ge=0),
):
    return coupons.preview(code, subtotal=subtotal)
