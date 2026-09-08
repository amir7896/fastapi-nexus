from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.saved_address import SavedAddress


class AddressRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_user(self, user_id: UUID) -> list[SavedAddress]:
        stmt = (
            select(SavedAddress)
            .where(SavedAddress.user_id == user_id)
            .order_by(SavedAddress.is_default.desc(), SavedAddress.created_at.desc())
        )
        return list(self._db.scalars(stmt).all())

    def get_for_user(self, address_id: UUID, user_id: UUID) -> SavedAddress | None:
        stmt = select(SavedAddress).where(
            SavedAddress.id == address_id,
            SavedAddress.user_id == user_id,
        )
        return self._db.scalar(stmt)

    def create(
        self,
        *,
        user_id: UUID,
        label: str | None,
        name: str,
        phone_country_code: str,
        phone: str,
        address: str,
        city: str,
        state: str,
        country: str,
        is_default: bool,
    ) -> SavedAddress:
        now = datetime.now(timezone.utc)
        item = SavedAddress(
            user_id=user_id,
            label=label,
            name=name,
            phone_country_code=phone_country_code,
            phone=phone,
            address=address,
            city=city,
            state=state,
            country=country,
            is_default=is_default,
            created_at=now,
            updated_at=now,
        )
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return item

    def save(self, item: SavedAddress) -> SavedAddress:
        item.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(item)
        return item

    def delete(self, item: SavedAddress) -> None:
        self._db.delete(item)
        self._db.commit()

    def clear_defaults(self, user_id: UUID, *, except_id: UUID | None = None) -> None:
        stmt = (
            update(SavedAddress)
            .where(SavedAddress.user_id == user_id, SavedAddress.is_default.is_(True))
        )
        if except_id is not None:
            stmt = stmt.where(SavedAddress.id != except_id)
        stmt = stmt.values(is_default=False, updated_at=datetime.now(timezone.utc))
        self._db.execute(stmt)
        self._db.commit()
