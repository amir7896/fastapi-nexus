from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.plans import DEFAULT_PLAN_ID
from app.models.organization import Organization, OrganizationInvite, OrganizationMembership
from app.models.user import User, UserRole


class OrganizationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        return self._db.get(Organization, organization_id)

    def get_by_slug(self, slug: str) -> Organization | None:
        return self._db.scalar(select(Organization).where(Organization.slug == slug.strip().lower()))

    def slug_exists(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        stmt = select(Organization.id).where(Organization.slug == slug.strip().lower())
        if exclude_id is not None:
            stmt = stmt.where(Organization.id != exclude_id)
        return self._db.scalar(stmt) is not None

    def create(
        self,
        *,
        name: str,
        slug: str,
        shop_url: str | None = None,
    ) -> Organization:
        now = datetime.now(timezone.utc)
        org = Organization(
            name=name.strip(),
            slug=slug.strip().lower(),
            shop_url=shop_url,
            plan=DEFAULT_PLAN_ID,
            plan_status="active",
            created_at=now,
            updated_at=now,
        )
        self._db.add(org)
        self._db.commit()
        self._db.refresh(org)
        return org

    def save(self, org: Organization) -> Organization:
        org.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(org)
        return org

    def has_admin(self, organization_id: UUID) -> bool:
        return (
            self._db.scalar(
                select(OrganizationMembership.id).where(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.role == UserRole.ADMIN,
                )
            )
            is not None
        )

    def get_membership(self, user_id: UUID, organization_id: UUID) -> OrganizationMembership | None:
        return self._db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
        )

    def list_memberships_for_user(self, user_id: UUID) -> list[OrganizationMembership]:
        return list(
            self._db.scalars(
                select(OrganizationMembership)
                .options(selectinload(OrganizationMembership.organization))
                .where(OrganizationMembership.user_id == user_id)
                .order_by(OrganizationMembership.created_at.asc())
            ).all()
        )

    def list_memberships(
        self,
        organization_id: UUID,
        *,
        search: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[OrganizationMembership], int]:
        filters = [OrganizationMembership.organization_id == organization_id]
        stmt = (
            select(OrganizationMembership)
            .join(User, User.id == OrganizationMembership.user_id)
            .where(*filters)
        )
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(or_(User.name.ilike(pattern), User.email.ilike(pattern)))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self._db.scalar(count_stmt) or 0
        items = list(
            self._db.scalars(
                stmt.order_by(OrganizationMembership.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
            ).all()
        )
        return items, total

    def count_seats(self, organization_id: UUID) -> int:
        staff = list(UserRole)
        staff.remove(UserRole.USER)
        pending = self._db.scalar(
            select(func.count(OrganizationInvite.id)).where(
                OrganizationInvite.organization_id == organization_id,
                OrganizationInvite.accepted_at.is_(None),
                OrganizationInvite.role != UserRole.USER,
            )
        ) or 0
        members = self._db.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.role != UserRole.USER,
                    OrganizationMembership.is_active.is_(True),
            )
        ) or 0
        return int(members) + int(pending)

    def count_staff_members(self, organization_id: UUID) -> int:
        return int(
            self._db.scalar(
                select(func.count(OrganizationMembership.id)).where(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.role != UserRole.USER,
                )
            )
            or 0
        )

    def list_users_by_roles(self, organization_id: UUID, roles: set[UserRole]) -> list[User]:
        if not roles:
            return []
        return list(
            self._db.scalars(
                select(User)
                .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
                .where(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.role.in_(roles),
                    OrganizationMembership.is_active.is_(True),
                )
                .order_by(User.name.asc())
            ).all()
        )

    def list_staff(self, organization_id: UUID, *, exclude_id: UUID) -> list[User]:
        return list(
            self._db.scalars(
                select(User)
                .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
                .where(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.role != UserRole.USER,
                    User.id != exclude_id,
                )
                .order_by(User.name.asc())
            ).all()
        )

    def add_membership(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        role: UserRole,
    ) -> OrganizationMembership:
        existing = self.get_membership(user_id, organization_id)
        if existing is not None:
            existing.role = role
            self._db.commit()
            self._db.refresh(existing)
            return existing
        row = OrganizationMembership(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    def set_membership_role(self, membership: OrganizationMembership, role: UserRole) -> OrganizationMembership:
        membership.role = role
        self._db.commit()
        self._db.refresh(membership)
        return membership

    def set_membership_active(self, membership: OrganizationMembership, is_active: bool) -> OrganizationMembership:
        membership.is_active = is_active
        self._db.commit()
        self._db.refresh(membership)
        return membership

    def delete_membership(self, membership: OrganizationMembership) -> None:
        self._db.delete(membership)
        self._db.commit()

    def count_admins(self, organization_id: UUID, *, exclude_user_id: UUID | None = None) -> int:
        stmt = select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == UserRole.ADMIN,
            OrganizationMembership.is_active.is_(True),
        )
        if exclude_user_id is not None:
            stmt = stmt.where(OrganizationMembership.user_id != exclude_user_id)
        return int(self._db.scalar(stmt) or 0)

    def get_invite_by_token_hash(self, token_hash: str) -> OrganizationInvite | None:
        return self._db.scalar(
            select(OrganizationInvite).where(OrganizationInvite.token_hash == token_hash)
        )

    def get_invite_by_id(self, invite_id: UUID) -> OrganizationInvite | None:
        return self._db.get(OrganizationInvite, invite_id)

    def get_pending_invite(self, organization_id: UUID, email: str) -> OrganizationInvite | None:
        return self._db.scalar(
            select(OrganizationInvite).where(
                OrganizationInvite.organization_id == organization_id,
                OrganizationInvite.email == email.strip().lower(),
                OrganizationInvite.accepted_at.is_(None),
            )
        )

    def list_pending_invites(self, organization_id: UUID) -> list[OrganizationInvite]:
        return list(
            self._db.scalars(
                select(OrganizationInvite)
                .where(
                    OrganizationInvite.organization_id == organization_id,
                    OrganizationInvite.accepted_at.is_(None),
                )
                .order_by(OrganizationInvite.created_at.desc())
            ).all()
        )

    def create_invite(
        self,
        *,
        organization_id: UUID,
        email: str,
        role: UserRole,
        token_hash: str,
        invited_by_id: UUID | None,
        expires_at: datetime,
    ) -> OrganizationInvite:
        invite = OrganizationInvite(
            organization_id=organization_id,
            email=email.strip().lower(),
            role=role,
            token_hash=token_hash,
            invited_by_id=invited_by_id,
            expires_at=expires_at,
        )
        self._db.add(invite)
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def mark_invite_accepted(self, invite: OrganizationInvite) -> OrganizationInvite:
        invite.accepted_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(invite)
        return invite

    def delete_invite(self, invite: OrganizationInvite) -> None:
        self._db.delete(invite)
        self._db.commit()

    def get_by_billing_customer(self, customer_id: str) -> Organization | None:
        return self._db.scalar(
            select(Organization).where(Organization.stripe_billing_customer_id == customer_id)
        )

    def get_by_subscription(self, subscription_id: str) -> Organization | None:
        return self._db.scalar(
            select(Organization).where(Organization.stripe_subscription_id == subscription_id)
        )
