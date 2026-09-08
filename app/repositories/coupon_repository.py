from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenant import require_organization_id
from app.models.coupon import Coupon


class CouponRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Coupon]:
        org_id = require_organization_id(self._db)
        return list(
            self._db.scalars(
                select(Coupon)
                .where(Coupon.organization_id == org_id)
                .order_by(Coupon.created_at.desc())
            ).all()
        )

    def get_by_id(self, coupon_id: UUID) -> Coupon | None:
        org_id = require_organization_id(self._db)
        return self._db.scalar(
            select(Coupon).where(Coupon.id == coupon_id, Coupon.organization_id == org_id)
        )

    def get_by_code(self, code: str) -> Coupon | None:
        org_id = require_organization_id(self._db)
        return self._db.scalar(
            select(Coupon).where(
                Coupon.organization_id == org_id,
                Coupon.code == code.strip().upper(),
            )
        )

    def create(self, **kwargs) -> Coupon:
        row = Coupon(organization_id=require_organization_id(self._db), **kwargs)
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def save(self, row: Coupon) -> Coupon:
        self._db.commit()
        self._db.refresh(row)
        return row

    def delete(self, row: Coupon) -> None:
        self._db.delete(row)
        self._db.commit()

    def increment_used(self, row: Coupon) -> Coupon:
        row.used_count = (row.used_count or 0) + 1
        return self.save(row)

    def is_usable(self, row: Coupon) -> bool:
        if not row.is_active:
            return False
        if row.expires_at is not None:
            expires = row.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return False
        if row.max_uses is not None and (row.used_count or 0) >= row.max_uses:
            return False
        return True
