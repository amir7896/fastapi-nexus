import re
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import stripe

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.core.plans import DEFAULT_PLAN_ID, PLANS, get_plan
from app.core.security import create_access_token, hash_otp, hash_password
from app.core.tenant import require_organization_id
from app.helpers.image_types import STORE_LOGO_FOLDER
from app.models.organization import Organization
from app.models.user import STAFF_ROLES, User, UserRole, as_role
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse
from app.schemas.common import MessageResponse
from app.schemas.organization import (
    BillingCheckoutRequest,
    BillingCheckoutResponse,
    BillingInvoiceRead,
    BillingPortalResponse,
    BillingResponse,
    InviteAcceptRequest,
    InviteCreateRequest,
    InviteListResponse,
    InvitePreview,
    InviteRead,
    MembershipRead,
    OrganizationCreateRequest,
    OrganizationRead,
    OrganizationResponse,
    OrganizationUpdateRequest,
    PlanRead,
    SwitchOrganizationRequest,
    PublicStoreRead,
    PublicStoreResponse,
    TeamMemberRead,
    TeamMemberUpdateRequest,
    TeamResponse,
)
from app.schemas.user import UserRead
from app.services.email_service import EmailService
from app.services.image_storage_service import ImageStorageService

logger = get_logger(__name__)

_INVITE_ROLES = {
    UserRole.MANAGER,
    UserRole.FINANCE,
    UserRole.SUPPORT,
    UserRole.FULFILLMENT,
}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return (slug or "store")[:80]


class OrganizationService:
    def __init__(
        self,
        organizations: OrganizationRepository,
        users: UserRepository,
        products: ProductRepository,
        emails: EmailService,
        images: ImageStorageService | None = None,
    ) -> None:
        self._organizations = organizations
        self._users = users
        self._products = products
        self._emails = emails
        self._images = images or ImageStorageService()

    def default_organization(self) -> Organization:
        settings = get_settings()
        org = self._organizations.get_by_slug(settings.DEFAULT_ORGANIZATION_SLUG)
        if org is not None:
            return org
        return self._organizations.create(
            name=settings.PROJECT_NAME,
            slug=settings.DEFAULT_ORGANIZATION_SLUG,
            shop_url=settings.SHOP_APP_URL,
        )

    def public_store(self, slug: str | None = None) -> PublicStoreResponse:
        settings = get_settings()
        org = self._organizations.get_by_slug((slug or settings.DEFAULT_ORGANIZATION_SLUG).strip().lower())
        if org is None:
            org = self.default_organization()
        return PublicStoreResponse(
            message="Store fetched",
            store=PublicStoreRead(name=org.name, slug=org.slug, logo_url=org.logo_url),
        )

    def get_current(self, current_user: User) -> OrganizationResponse:
        org = self._require_org(current_user)
        return OrganizationResponse(message="Store fetched", organization=OrganizationRead.model_validate(org))

    def create_store(self, payload: OrganizationCreateRequest, *, current_user: User) -> AuthResponse:
        if as_role(current_user.role) not in STAFF_ROLES:
            raise ForbiddenError("Customers cannot create a store")
        org = self._create_organization(payload.name, payload.slug)
        self._organizations.add_membership(
            user_id=current_user.id,
            organization_id=org.id,
            role=UserRole.ADMIN,
        )
        return self._activate(current_user, org, UserRole.ADMIN, "Store created")

    def update_settings(
        self,
        payload: OrganizationUpdateRequest,
        *,
        current_user: User,
    ) -> OrganizationResponse:
        self._require_settings_access(current_user)
        org = self._require_org(current_user)
        org.name = payload.name.strip()
        org.currency = payload.currency.strip().lower()
        org.timezone = payload.timezone.strip() or "UTC"
        org.tax_rate = payload.tax_rate
        org.shipping_flat_rate = payload.shipping_flat_rate
        org.notify_orders = payload.notify_orders
        org.notify_low_stock = payload.notify_low_stock
        org.shop_url = payload.shop_url.strip() if payload.shop_url else None
        saved = self._organizations.save(org)
        return OrganizationResponse(message="Store settings saved", organization=OrganizationRead.model_validate(saved))

    def upload_logo(self, upload: UploadFile, *, current_user: User) -> OrganizationResponse:
        self._require_settings_access(current_user)
        org = self._require_org(current_user)
        stored = self._images.upload(upload, folder=STORE_LOGO_FOLDER)
        previous_id = org.logo_public_id
        org.logo_url = stored.url
        org.logo_public_id = stored.public_id
        saved = self._organizations.save(org)
        if previous_id and previous_id != stored.public_id:
            self._images.delete(previous_id, missing_ok=True)
        logger.info("Uploaded logo for store %s via %s", saved.slug, stored.provider)
        return OrganizationResponse(message="Store logo uploaded", organization=OrganizationRead.model_validate(saved))

    def delete_logo(self, *, current_user: User) -> OrganizationResponse:
        self._require_settings_access(current_user)
        org = self._require_org(current_user)
        if org.logo_public_id:
            self._images.delete(org.logo_public_id, missing_ok=True)
        org.logo_url = None
        org.logo_public_id = None
        saved = self._organizations.save(org)
        logger.info("Removed logo for store %s", saved.slug)
        return OrganizationResponse(message="Store logo removed", organization=OrganizationRead.model_validate(saved))

    def list_memberships(self, *, current_user: User) -> list[MembershipRead]:
        rows = self._organizations.list_memberships_for_user(current_user.id)
        return [
            MembershipRead(
                organization_id=row.organization_id,
                organization_slug=row.organization.slug,
                organization_name=row.organization.name,
                logo_url=row.organization.logo_url,
                role=row.role,
                plan=row.organization.plan,
            )
            for row in rows
            if row.organization is not None
        ]

    def switch(self, payload: SwitchOrganizationRequest, *, current_user: User) -> AuthResponse:
        membership = self._organizations.get_membership(current_user.id, payload.organization_id)
        if membership is None:
            raise ForbiddenError("You do not belong to that store")
        org = self._organizations.get_by_id(payload.organization_id)
        if org is None:
            raise NotFoundError("Store not found")
        return self._activate(current_user, org, membership.role, "Switched store")

    def team(self, *, current_user: User) -> TeamResponse:
        self._require_admin(current_user)
        org = self._require_org(current_user)
        members, _ = self._organizations.list_memberships(org.id, page=1, limit=100)
        invites = self._organizations.list_pending_invites(org.id)
        plan = get_plan(org.plan)
        return TeamResponse(
            message="Team fetched",
            members=[
                TeamMemberRead(
                    id=row.id,
                    user_id=row.user_id,
                    name=row.user.name if row.user else "",
                    email=row.user.email if row.user else "",
                    role=row.role,
                    is_active=getattr(row, "is_active", True),
                    created_at=row.created_at,
                )
                for row in members
                if as_role(row.role) in STAFF_ROLES
            ],
            invites=[self._invite_read(item) for item in invites],
            seats_used=self._organizations.count_seats(org.id),
            seat_limit=plan.seats,
        )

    def invite(self, payload: InviteCreateRequest, *, current_user: User) -> InviteRead:
        self._require_admin(current_user)
        if payload.role not in _INVITE_ROLES:
            raise BadRequestError("Invite a staff role")
        org = self._require_org(current_user)
        self.ensure_seat_available(org, extra=1)
        email = str(payload.email).strip().lower()
        existing_member = None
        existing_user = self._users.get_by_email(email)
        if existing_user is not None:
            existing_member = self._organizations.get_membership(existing_user.id, org.id)
        if existing_member is not None:
            raise ConflictError("That person is already on this store")
        pending = self._organizations.get_pending_invite(org.id, email)
        if pending is not None:
            self._organizations.delete_invite(pending)
        settings = get_settings()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.INVITE_EXPIRE_DAYS)
        invite = self._organizations.create_invite(
            organization_id=org.id,
            email=email,
            role=payload.role,
            token_hash=hash_otp(token),
            invited_by_id=current_user.id,
            expires_at=expires_at,
        )
        accept_url = f"{settings.SHOP_APP_URL.rstrip('/')}/invite/{token}"
        self._emails.send_staff_invite(
            to_email=email,
            organization_name=org.name,
            role=payload.role.value.title(),
            accept_url=accept_url,
            inviter_name=current_user.name,
        )
        logger.info("Invited %s to store %s as %s", email, org.slug, payload.role.value)
        return self._invite_read(invite)

    def preview_invite(self, token: str) -> InvitePreview:
        invite = self._valid_invite(token)
        existing = self._users.get_by_email(invite.email)
        return InvitePreview(
            message="Invite found",
            email=invite.email,
            role=invite.role,
            organization_name=invite.organization.name if invite.organization else "",
            needs_account=existing is None,
        )

    def accept_invite(self, payload: InviteAcceptRequest) -> AuthResponse:
        invite = self._valid_invite(payload.token)
        org = invite.organization or self._organizations.get_by_id(invite.organization_id)
        if org is None:
            raise NotFoundError("Store not found")
        user = self._users.get_by_email(invite.email)
        if user is None:
            if not payload.name or not payload.password:
                raise BadRequestError("Name and password are required to join")
            user = self._users.create(
                name=payload.name,
                email=invite.email,
                password_hash=hash_password(payload.password),
                role=invite.role,
                email_verified=True,
            )
        self._organizations.add_membership(
            user_id=user.id,
            organization_id=org.id,
            role=invite.role,
        )
        self._organizations.mark_invite_accepted(invite)
        logger.info("User %s joined store %s via invite", user.email, org.slug)
        return self._activate(user, org, invite.role, "Joined store")

    def revoke_invite(self, invite_id: UUID, *, current_user: User) -> MessageResponse:
        self._require_admin(current_user)
        org = self._require_org(current_user)
        invite = self._organizations.get_invite_by_id(invite_id)
        if invite is None or invite.organization_id != org.id:
            raise NotFoundError("Invite not found")
        self._organizations.delete_invite(invite)
        return MessageResponse(message="Invite revoked")

    def update_member(
        self,
        user_id: UUID,
        payload: TeamMemberUpdateRequest,
        *,
        current_user: User,
    ) -> TeamResponse:
        self._require_admin(current_user)
        org = self._require_org(current_user)
        if user_id == current_user.id:
            raise ForbiddenError("You cannot change your own team access")
        membership = self._organizations.get_membership(user_id, org.id)
        if membership is None or as_role(membership.role) not in STAFF_ROLES:
            raise NotFoundError("Staff member not found")
        if payload.role is not None:
            if payload.role not in STAFF_ROLES:
                raise BadRequestError("Assign a staff role")
            if as_role(membership.role) is UserRole.ADMIN and self._organizations.count_admins(
                org.id, exclude_user_id=user_id
            ) < 1:
                raise BadRequestError("Keep at least one active admin")
            self._organizations.set_membership_role(membership, payload.role)
            member = self._users.get_by_id_global(user_id)
            if member is not None and member.active_organization_id == org.id:
                self._users.update(member, name=member.name, age=member.age, role=payload.role)
        if payload.is_active is not None:
            if (
                payload.is_active is False
                and as_role(membership.role) is UserRole.ADMIN
                and self._organizations.count_admins(org.id, exclude_user_id=user_id) < 1
            ):
                raise BadRequestError("Keep at least one active admin")
            self._organizations.set_membership_active(membership, payload.is_active)
        return self.team(current_user=current_user)

    def remove_member(self, user_id: UUID, *, current_user: User) -> MessageResponse:
        self._require_admin(current_user)
        org = self._require_org(current_user)
        if user_id == current_user.id:
            raise ForbiddenError("You cannot remove yourself")
        membership = self._organizations.get_membership(user_id, org.id)
        if membership is None or as_role(membership.role) not in STAFF_ROLES:
            raise NotFoundError("Staff member not found")
        if as_role(membership.role) is UserRole.ADMIN and self._organizations.count_admins(
            org.id, exclude_user_id=user_id
        ) < 1:
            raise BadRequestError("Keep at least one active admin")
        self._organizations.delete_membership(membership)
        member = self._users.get_by_id_global(user_id)
        if member is not None:
            remaining = [
                row
                for row in self._organizations.list_memberships_for_user(user_id)
                if as_role(row.role) in STAFF_ROLES and getattr(row, "is_active", True)
            ]
            if not remaining:
                self._users.update(member, name=member.name, age=member.age, role=UserRole.USER)
            elif member.active_organization_id == org.id:
                member.active_organization_id = remaining[0].organization_id
                self._users.update(member, name=member.name, age=member.age, role=remaining[0].role)
        return MessageResponse(message="Staff member removed")

    def billing(self, *, current_user: User, session_id: str | None = None) -> BillingResponse:
        self._require_admin(current_user)
        org = self._require_org(current_user)
        settings = get_settings()
        if settings.stripe_enabled:
            self._sync_subscription_from_stripe(org, session_id=session_id)
            org = self._require_org(current_user)
        invoices: list[BillingInvoiceRead] = []
        if settings.stripe_enabled and org.stripe_billing_customer_id:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            try:
                result = stripe.Invoice.list(customer=org.stripe_billing_customer_id, limit=12)
                for item in result.data:
                    invoices.append(
                        BillingInvoiceRead(
                            id=item.id,
                            number=item.number,
                            amount=str(Decimal(item.amount_paid or 0) / Decimal(100)),
                            currency=(item.currency or org.currency).upper(),
                            status=item.status,
                            hosted_invoice_url=item.hosted_invoice_url,
                            created=item.created,
                        )
                    )
            except stripe.StripeError:
                logger.warning("Could not list invoices for store %s", org.id)
        price_ids = {"pro": settings.STRIPE_PRICE_PRO, "business": settings.STRIPE_PRICE_BUSINESS}
        plans = [
            PlanRead(
                id=plan.id,
                name=plan.name,
                seats=plan.seats,
                products=plan.products,
                description=plan.description,
                current=plan.id == org.plan,
                price_configured=plan.id == DEFAULT_PLAN_ID or bool(price_ids.get(plan.id, "").strip()),
            )
            for plan in PLANS.values()
        ]
        return BillingResponse(
            message="Billing fetched",
            plan=org.plan,
            plan_status=org.plan_status,
            plans=plans,
            invoices=invoices,
            portal_available=bool(org.stripe_billing_customer_id and settings.stripe_enabled),
        )

    def billing_checkout(
        self,
        payload: BillingCheckoutRequest,
        *,
        current_user: User,
    ) -> BillingCheckoutResponse:
        self._require_admin(current_user)
        org = self._require_org(current_user)
        plan_id = payload.plan.strip().lower()
        if plan_id not in {"pro", "business"}:
            raise BadRequestError("Choose Pro or Business")
        settings = get_settings()
        if not settings.stripe_enabled:
            raise BadRequestError("Stripe is not configured")
        price_id = (
            settings.STRIPE_PRICE_PRO.strip()
            if plan_id == "pro"
            else settings.STRIPE_PRICE_BUSINESS.strip()
        )
        if not price_id:
            raise BadRequestError("That plan is not configured yet")
        stripe.api_key = settings.STRIPE_SECRET_KEY
        customer_id = self._billing_customer(org, current_user)
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer=customer_id,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=settings.STRIPE_BILLING_SUCCESS_URL,
                cancel_url=settings.STRIPE_BILLING_CANCEL_URL,
                metadata={"purpose": "billing", "organization_id": str(org.id), "plan": plan_id},
                subscription_data={
                    "metadata": {
                        "purpose": "billing",
                        "organization_id": str(org.id),
                        "plan": plan_id,
                    }
                },
            )
        except stripe.StripeError as exc:
            logger.warning("Billing checkout failed for store %s: %s", org.id, exc)
            raise BadRequestError("Could not start billing checkout") from exc
        if not session.url:
            raise BadRequestError("Could not start billing checkout")
        return BillingCheckoutResponse(message="Checkout created", checkout_url=session.url)

    def billing_portal(self, *, current_user: User) -> BillingPortalResponse:
        self._require_admin(current_user)
        org = self._require_org(current_user)
        settings = get_settings()
        if not settings.stripe_enabled or not org.stripe_billing_customer_id:
            raise BadRequestError("No billing account yet")
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.billing_portal.Session.create(
                customer=org.stripe_billing_customer_id,
                return_url=settings.STRIPE_BILLING_PORTAL_RETURN_URL,
            )
        except stripe.StripeError as exc:
            raise BadRequestError("Could not open the billing portal") from exc
        return BillingPortalResponse(message="Portal created", portal_url=session.url)

    def _plan_id_from_price(self, price_id: str | None) -> str | None:
        if not price_id:
            return None
        settings = get_settings()
        if price_id == settings.STRIPE_PRICE_PRO.strip():
            return "pro"
        if price_id == settings.STRIPE_PRICE_BUSINESS.strip():
            return "business"
        return None

    def _plan_id_from_subscription(self, subscription) -> str | None:
        metadata = getattr(subscription, "metadata", None) or {}
        if isinstance(subscription, dict):
            metadata = subscription.get("metadata") or {}
        plan_id = metadata.get("plan") if isinstance(metadata, dict) else None
        if plan_id in PLANS:
            return plan_id
        items = getattr(subscription, "items", None)
        data = []
        if items is not None:
            data = getattr(items, "data", None) or []
        elif isinstance(subscription, dict):
            data = ((subscription.get("items") or {}).get("data") or [])
        if not data:
            return None
        first = data[0]
        price = getattr(first, "price", None)
        if price is None and isinstance(first, dict):
            price = first.get("price")
        price_id = getattr(price, "id", None)
        if price_id is None and isinstance(price, dict):
            price_id = price.get("id")
        if price_id is None and isinstance(price, str):
            price_id = price
        return self._plan_id_from_price(price_id)

    def _sync_subscription_from_stripe(self, org: Organization, *, session_id: str | None = None) -> None:
        settings = get_settings()
        if not settings.stripe_enabled:
            return
        stripe.api_key = settings.STRIPE_SECRET_KEY
        if session_id and session_id.startswith("cs_"):
            try:
                session = stripe.checkout.Session.retrieve(session_id, expand=["subscription"])
                metadata = session.get("metadata") or {}
                if metadata.get("purpose") == "billing":
                    subscription = session.get("subscription")
                    subscription_id = (
                        subscription
                        if isinstance(subscription, str)
                        else getattr(subscription, "id", None)
                    )
                    plan_id = metadata.get("plan")
                    if not plan_id and subscription is not None and not isinstance(subscription, str):
                        plan_id = self._plan_id_from_subscription(subscription)
                    self.apply_subscription(
                        organization_id=org.id,
                        customer_id=session.get("customer")
                        if isinstance(session.get("customer"), str)
                        else None,
                        subscription_id=subscription_id,
                        plan_id=plan_id,
                        status="active",
                    )
                    org = self._organizations.get_by_id(org.id) or org
            except stripe.StripeError:
                logger.warning("Could not retrieve billing checkout session for store %s", org.id)
        customer_id = org.stripe_billing_customer_id
        if not customer_id:
            return
        try:
            result = stripe.Subscription.list(customer=customer_id, status="all", limit=12)
        except stripe.StripeError:
            logger.warning("Could not list subscriptions for store %s", org.id)
            return
        chosen = None
        for row in result.data:
            status = (getattr(row, "status", None) or "").lower()
            if status in {"active", "trialing", "past_due"}:
                chosen = row
                break
        if chosen is None:
            if session_id:
                return
            if org.plan != DEFAULT_PLAN_ID:
                self.apply_subscription(
                    organization_id=org.id,
                    customer_id=customer_id,
                    status="canceled",
                )
            return
        self.apply_subscription(
            organization_id=org.id,
            customer_id=customer_id,
            subscription_id=getattr(chosen, "id", None),
            plan_id=self._plan_id_from_subscription(chosen),
            status=getattr(chosen, "status", None),
        )

    def apply_subscription(
        self,
        *,
        organization_id: UUID | None = None,
        customer_id: str | None = None,
        subscription_id: str | None = None,
        plan_id: str | None = None,
        status: str | None = None,
    ) -> None:
        org = None
        if organization_id is not None:
            org = self._organizations.get_by_id(organization_id)
        if org is None and customer_id:
            org = self._organizations.get_by_billing_customer(customer_id)
        if org is None and subscription_id:
            org = self._organizations.get_by_subscription(subscription_id)
        if org is None:
            return
        if customer_id:
            org.stripe_billing_customer_id = customer_id
        if subscription_id:
            org.stripe_subscription_id = subscription_id
        if plan_id in PLANS:
            org.plan = plan_id
        normalized = (status or "").lower()
        if normalized in {"active", "trialing"}:
            org.plan_status = "active"
        elif normalized in {"canceled", "unpaid", "incomplete_expired"}:
            org.plan = DEFAULT_PLAN_ID
            org.plan_status = "canceled"
            org.stripe_subscription_id = None
        elif normalized:
            org.plan_status = normalized
        self._organizations.save(org)

    def ensure_seat_available(self, org: Organization, *, extra: int = 0) -> None:
        plan = get_plan(org.plan)
        used = self._organizations.count_seats(org.id) + extra
        if used > plan.seats:
            raise BadRequestError(
                f"{plan.name} includes {plan.seats} staff seats. Upgrade to invite more people."
            )

    def ensure_product_available(self, org: Organization | None = None) -> None:
        organization = org or self._organizations.get_by_id(require_organization_id(self._organizations._db))
        if organization is None:
            return
        plan = get_plan(organization.plan)
        count = self._products.count_active(organization_id=organization.id)
        if count >= plan.products:
            raise BadRequestError(
                f"{plan.name} includes {plan.products} products. Upgrade to add more."
            )

    def attach_user(
        self,
        user: User,
        *,
        role: UserRole,
        store_name: str | None = None,
        store_slug: str | None = None,
    ) -> Organization:
        membership_role = as_role(role)
        if store_name:
            org = self._create_organization(store_name, store_slug)
            membership_role = UserRole.ADMIN
        elif store_slug:
            org = self._organizations.get_by_slug(store_slug)
            if org is None:
                raise NotFoundError("Store not found")
        else:
            org = self.default_organization()
        self._organizations.add_membership(
            user_id=user.id,
            organization_id=org.id,
            role=membership_role,
        )
        self._users.set_active_organization(user, org.id, role=membership_role)
        return org

    def ensure_membership(self, user: User, *, staff: bool = False) -> tuple[Organization, UserRole]:
        memberships = self._organizations.list_memberships_for_user(user.id)
        account_role = as_role(user.role) if user.role else UserRole.USER

        def role_for(row) -> UserRole:
            membership_role = as_role(row.role)
            if account_role in STAFF_ROLES and membership_role not in STAFF_ROLES:
                self._organizations.set_membership_role(row, account_role)
                return account_role
            return membership_role

        if user.active_organization_id:
            for row in memberships:
                if row.organization_id == user.active_organization_id:
                    role = role_for(row)
                    if staff and role not in STAFF_ROLES:
                        continue
                    org = row.organization or self._organizations.get_by_id(row.organization_id)
                    if org is None:
                        break
                    return org, role
        if staff:
            for row in memberships:
                if as_role(row.role) in STAFF_ROLES and row.organization is not None:
                    return row.organization, as_role(row.role)
            if account_role not in STAFF_ROLES:
                raise ForbiddenError("Staff access required")
            org = (
                self._organizations.get_by_id(user.active_organization_id)
                if user.active_organization_id
                else None
            ) or self.default_organization()
            self._organizations.add_membership(
                user_id=user.id,
                organization_id=org.id,
                role=account_role,
            )
            return org, account_role
        if memberships and memberships[0].organization is not None:
            return memberships[0].organization, role_for(memberships[0])
        org = self.default_organization()
        if staff and account_role not in STAFF_ROLES:
            raise ForbiddenError("Staff access required")
        self._organizations.add_membership(user_id=user.id, organization_id=org.id, role=account_role)
        return org, account_role

    def activate_current(self, user: User, *, staff: bool = False) -> AuthResponse:
        org, role = self.ensure_membership(user, staff=staff)
        message = "Staff login successful" if staff else "Login successful"
        return self._activate(user, org, role, message)

    def user_read(self, user: User) -> UserRead:
        org = None
        if user.active_organization_id:
            org = self._organizations.get_by_id(user.active_organization_id)
        return UserRead.from_user(user, org)

    def _activate(self, user: User, org: Organization, role: UserRole, message: str) -> AuthResponse:
        membership_role = as_role(role)
        updated = self._users.set_active_organization(user, org.id, role=membership_role)
        token = create_access_token(
            user_id=updated.id,
            email=updated.email,
            role=as_role(updated.role).value,
            organization_id=org.id,
        )
        return AuthResponse(
            message=message,
            user=UserRead.from_user(updated, org),
            access_token=token,
            token_type="bearer",
        )

    def _create_organization(self, name: str, slug: str | None) -> Organization:
        base = slugify(slug or name)
        candidate = base
        suffix = 2
        while self._organizations.slug_exists(candidate):
            candidate = f"{base}-{suffix}"[:80]
            suffix += 1
        return self._organizations.create(name=name, slug=candidate)

    def _require_org(self, user: User) -> Organization:
        org_id = user.active_organization_id
        if org_id is None:
            org_id = require_organization_id(self._organizations._db)
        org = self._organizations.get_by_id(org_id) if org_id else None
        if org is not None:
            membership = self._organizations.get_membership(user.id, org.id)
            if membership is not None:
                return org
        org, role = self.ensure_membership(user, staff=as_role(user.role) in STAFF_ROLES)
        user.active_organization_id = org.id
        user.role = role
        return org

    def _require_admin(self, user: User) -> None:
        if as_role(user.role) is not UserRole.ADMIN:
            raise ForbiddenError("Admin access required")

    def _require_settings_access(self, user: User) -> None:
        if as_role(user.role) not in {UserRole.ADMIN, UserRole.MANAGER}:
            raise ForbiddenError("Store settings access required")

    def _valid_invite(self, token: str):
        invite = self._organizations.get_invite_by_token_hash(hash_otp(token))
        if invite is None or invite.accepted_at is not None:
            raise BadRequestError("Invite is invalid or expired")
        expires_at = invite.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise BadRequestError("Invite is invalid or expired")
        return invite

    def _invite_read(self, invite) -> InviteRead:
        return InviteRead(
            id=invite.id,
            email=invite.email,
            role=invite.role,
            organization_name=invite.organization.name if invite.organization else "",
            expires_at=invite.expires_at,
            created_at=invite.created_at,
        )

    def _billing_customer(self, org: Organization, user: User) -> str:
        settings = get_settings()
        stripe.api_key = settings.STRIPE_SECRET_KEY
        existing = (org.stripe_billing_customer_id or "").strip()
        if existing:
            try:
                stripe.Customer.retrieve(existing)
                return existing
            except stripe.InvalidRequestError:
                logger.warning(
                    "Stored billing customer %s is missing in Stripe; creating a new one for store %s",
                    existing,
                    org.id,
                )
                org.stripe_billing_customer_id = None
                org.stripe_subscription_id = None
        customer = stripe.Customer.create(
            email=user.email,
            name=org.name,
            metadata={"organization_id": str(org.id)},
        )
        org.stripe_billing_customer_id = customer.id
        self._organizations.save(org)
        return customer.id
