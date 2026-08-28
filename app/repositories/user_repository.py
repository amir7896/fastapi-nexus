from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.strip().lower())
        return self._db.scalar(stmt)

    def exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def list_paginated(
        self,
        *,
        page: int,
        limit: int,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        filters = []
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    User.name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        count_stmt = select(func.count(User.id))
        list_stmt = select(User).order_by(User.created_at.desc())
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = self._db.scalar(count_stmt) or 0
        offset = (page - 1) * limit
        items = list(self._db.scalars(list_stmt.offset(offset).limit(limit)).all())
        return items, total

    def create(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
        age: int | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        user = User(
            name=name,
            email=email.strip().lower(),
            password_hash=password_hash,
            age=age,
            role=role,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update(self, user: User, *, name: str, age: int | None) -> User:
        user.name = name.strip()
        user.age = age
        self._db.commit()
        self._db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self._db.delete(user)
        self._db.commit()
