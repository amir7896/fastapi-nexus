from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.tenant import get_current_organization_id
from app.models.organization import OrganizationMembership
from app.models.user import STAFF_ROLES, User, UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        user = self._db.get(User, user_id)
        if user is None:
            return None
        org_id = get_current_organization_id(self._db)
        if org_id is None:
            return user
        membership = self._db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == org_id,
            )
        )
        if membership is None:
            return None
        user.role = membership.role
        return user

    def get_by_id_global(self, user_id: UUID) -> User | None:
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
        org_id = get_current_organization_id(self._db)
        filters = []
        if org_id is not None:
            filters.append(OrganizationMembership.organization_id == org_id)
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    User.name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        base = select(User)
        if org_id is not None:
            base = base.join(
                OrganizationMembership,
                OrganizationMembership.user_id == User.id,
            )
        count_stmt = select(func.count(User.id))
        if org_id is not None:
            count_stmt = select(func.count(User.id)).join(
                OrganizationMembership,
                OrganizationMembership.user_id == User.id,
            )
        list_stmt = base.order_by(User.created_at.desc())
        if filters:
            count_stmt = count_stmt.where(*filters)
            list_stmt = list_stmt.where(*filters)

        total = self._db.scalar(count_stmt) or 0
        offset = (page - 1) * limit
        items = list(self._db.scalars(list_stmt.offset(offset).limit(limit)).all())
        if org_id is not None:
            for user in items:
                membership = self._db.scalar(
                    select(OrganizationMembership).where(
                        OrganizationMembership.user_id == user.id,
                        OrganizationMembership.organization_id == org_id,
                    )
                )
                if membership is not None:
                    user.role = membership.role
        return items, total

    def list_staff(self, *, exclude_id: UUID) -> list[User]:
        org_id = get_current_organization_id(self._db)
        stmt = select(User).where(User.role.in_(STAFF_ROLES), User.id != exclude_id)
        if org_id is not None:
            stmt = (
                select(User)
                .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
                .where(
                    OrganizationMembership.organization_id == org_id,
                    OrganizationMembership.role.in_(STAFF_ROLES),
                    User.id != exclude_id,
                )
            )
        return list(self._db.scalars(stmt.order_by(User.name.asc())).all())

    def list_by_roles(self, roles: set[UserRole], organization_id: UUID | None = None) -> list[User]:
        if not roles:
            return []
        org_id = organization_id or get_current_organization_id(self._db)
        stmt = select(User).where(User.role.in_(roles))
        if org_id is not None:
            stmt = (
                select(User)
                .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
                .where(
                    OrganizationMembership.organization_id == org_id,
                    OrganizationMembership.role.in_(roles),
                    OrganizationMembership.is_active.is_(True),
                )
            )
        return list(self._db.scalars(stmt.order_by(User.name.asc())).all())

    def create(
        self,
        *,
        name: str,
        email: str,
        password_hash: str,
        age: int | None = None,
        role: UserRole = UserRole.USER,
        email_verified: bool = False,
    ) -> User:
        user = User(
            name=name,
            email=email.strip().lower(),
            password_hash=password_hash,
            age=age,
            role=role,
            email_verified=email_verified,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update(
        self,
        user: User,
        *,
        name: str,
        age: int | None,
        role: UserRole | None = None,
        email_verified: bool | None = None,
        notify_order_email: bool | None = None,
        notify_support_email: bool | None = None,
        notify_marketing_email: bool | None = None,
    ) -> User:
        user.name = name.strip()
        user.age = age
        if notify_order_email is not None:
            user.notify_order_email = notify_order_email
        if notify_support_email is not None:
            user.notify_support_email = notify_support_email
        if notify_marketing_email is not None:
            user.notify_marketing_email = notify_marketing_email
        if role is not None:
            user.role = role
            org_id = get_current_organization_id(self._db) or user.active_organization_id
            if org_id is not None:
                membership = self._db.scalar(
                    select(OrganizationMembership).where(
                        OrganizationMembership.user_id == user.id,
                        OrganizationMembership.organization_id == org_id,
                    )
                )
                if membership is not None:
                    membership.role = role
                else:
                    self._db.add(
                        OrganizationMembership(
                            user_id=user.id,
                            organization_id=org_id,
                            role=role,
                        )
                    )
        if email_verified is not None:
            user.email_verified = email_verified
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_password(self, user: User, *, password_hash: str) -> User:
        user.password_hash = password_hash
        self._db.commit()
        self._db.refresh(user)
        return user

    def set_stripe_customer_id(self, user: User, customer_id: str) -> User:
        user.stripe_customer_id = customer_id
        self._db.commit()
        self._db.refresh(user)
        return user

    def set_active_organization(
        self,
        user: User,
        organization_id: UUID | None,
        *,
        role: UserRole | None = None,
    ) -> User:
        user.active_organization_id = organization_id
        if role is not None:
            user.role = role
        self._db.commit()
        self._db.refresh(user)
        return user

    def mark_email_verified(self, user: User) -> User:
        user.email_verified = True
        self._db.commit()
        self._db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self._db.delete(user)
        self._db.commit()
