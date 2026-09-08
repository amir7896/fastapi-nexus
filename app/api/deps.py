from typing import Annotated
from uuid import UUID

from fastapi import Depends  # pyright: ignore[reportMissingImports]
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # pyright: ignore[reportMissingImports]
from jwt.exceptions import InvalidTokenError  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Session  # pyright: ignore[reportMissingImports]

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.core.tenant import get_current_organization_id, set_current_organization_id
from app.db.session import get_db
from app.models.user import User, UserRole, as_role
from app.repositories.address_repository import AddressRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.cart_repository import CartRepository
from app.repositories.coupon_repository import CouponRepository
from app.repositories.brand_repository import BrandRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.support_repository import SupportRepository
from app.repositories.product_variant_repository import ProductVariantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.wishlist_repository import WishlistRepository
from app.services.address_service import AddressService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.cart_service import CartService
from app.services.coupon_service import CouponService
from app.services.brand_service import BrandService
from app.services.category_service import CategoryService
from app.services.email_service import EmailService
from app.services.inbox_notification_service import InboxNotificationService
from app.services.location_service import LocationService
from app.services.order_service import OrderService
from app.services.organization_service import OrganizationService
from app.services.image_storage_service import ImageStorageService
from app.services.product_service import ProductService
from app.services.report_service import ReportService
from app.services.review_service import ReviewService
from app.services.stock_alert_service import StockAlertService
from app.services.support_service import SupportService
from app.services.stripe_payment_service import StripePaymentService
from app.services.user_service import UserService
from app.services.wishlist_service import WishlistService

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_category_repository(db: DbSession) -> CategoryRepository:
    return CategoryRepository(db)


def get_brand_repository(db: DbSession) -> BrandRepository:
    return BrandRepository(db)


def get_product_repository(db: DbSession) -> ProductRepository:
    return ProductRepository(db)


def get_product_variant_repository(db: DbSession) -> ProductVariantRepository:
    return ProductVariantRepository(db)


def get_notification_repository(db: DbSession) -> NotificationRepository:
    return NotificationRepository(db)


def get_order_repository(db: DbSession) -> OrderRepository:
    return OrderRepository(db)


def get_review_repository(db: DbSession) -> ReviewRepository:
    return ReviewRepository(db)


def get_support_repository(db: DbSession) -> SupportRepository:
    return SupportRepository(db)


def get_audit_repository(db: DbSession) -> AuditRepository:
    return AuditRepository(db)


def get_coupon_repository(db: DbSession) -> CouponRepository:
    return CouponRepository(db)


def get_cart_repository(db: DbSession) -> CartRepository:
    return CartRepository(db)


def get_address_repository(db: DbSession) -> AddressRepository:
    return AddressRepository(db)


def get_wishlist_repository(db: DbSession) -> WishlistRepository:
    return WishlistRepository(db)


def get_organization_repository(db: DbSession) -> OrganizationRepository:
    return OrganizationRepository(db)


def get_password_reset_repository(db: DbSession) -> PasswordResetRepository:
    return PasswordResetRepository(db)


def get_email_verification_repository(db: DbSession) -> EmailVerificationRepository:
    return EmailVerificationRepository(db)


def get_email_service() -> EmailService:
    return EmailService()


def get_inbox_notification_service(
    notifications: Annotated[NotificationRepository, Depends(get_notification_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> InboxNotificationService:
    return InboxNotificationService(notifications, users)


def get_audit_service(
    logs: Annotated[AuditRepository, Depends(get_audit_repository)],
) -> AuditService:
    return AuditService(logs)


def get_stock_alert_service(
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    emails: Annotated[EmailService, Depends(get_email_service)],
) -> StockAlertService:
    return StockAlertService(products, users, emails)


def get_image_storage_service() -> ImageStorageService:
    return ImageStorageService()


def get_organization_service(
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    emails: Annotated[EmailService, Depends(get_email_service)],
    images: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> OrganizationService:
    return OrganizationService(organizations, users, products, emails, images)


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    password_resets: Annotated[PasswordResetRepository, Depends(get_password_reset_repository)],
    email_verifications: Annotated[
        EmailVerificationRepository,
        Depends(get_email_verification_repository),
    ],
    emails: Annotated[EmailService, Depends(get_email_service)],
    organizations: Annotated[OrganizationService, Depends(get_organization_service)],
) -> AuthService:
    service = AuthService(users, password_resets, email_verifications, emails)
    service.bind_organizations(organizations)
    return service


def get_category_service(
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> CategoryService:
    return CategoryService(categories)


def get_brand_service(
    brands: Annotated[BrandRepository, Depends(get_brand_repository)],
) -> BrandService:
    return BrandService(brands)


def get_product_service(
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
    brands: Annotated[BrandRepository, Depends(get_brand_repository)],
    variants: Annotated[ProductVariantRepository, Depends(get_product_variant_repository)],
    images: Annotated[ImageStorageService, Depends(get_image_storage_service)],
    stock_alerts: Annotated[StockAlertService, Depends(get_stock_alert_service)],
    organizations: Annotated[OrganizationService, Depends(get_organization_service)],
) -> ProductService:
    return ProductService(products, categories, brands, variants, images, stock_alerts, organizations)


def get_stripe_payment_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    organizations: Annotated[OrganizationService, Depends(get_organization_service)],
) -> StripePaymentService:
    return StripePaymentService(orders, users, organizations)


def get_location_service() -> LocationService:
    return LocationService()


def get_order_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    variants: Annotated[ProductVariantRepository, Depends(get_product_variant_repository)],
    stripe_payments: Annotated[StripePaymentService, Depends(get_stripe_payment_service)],
    emails: Annotated[EmailService, Depends(get_email_service)],
    locations: Annotated[LocationService, Depends(get_location_service)],
    stock_alerts: Annotated[StockAlertService, Depends(get_stock_alert_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> OrderService:
    return OrderService(
        orders,
        products,
        variants,
        stripe_payments,
        emails,
        locations,
        stock_alerts,
        audit,
    )


def get_report_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
) -> ReportService:
    return ReportService(orders)


def get_coupon_service(
    coupons: Annotated[CouponRepository, Depends(get_coupon_repository)],
) -> CouponService:
    return CouponService(coupons)


def get_cart_service(
    cart: Annotated[CartRepository, Depends(get_cart_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    variants: Annotated[ProductVariantRepository, Depends(get_product_variant_repository)],
    orders: Annotated[OrderService, Depends(get_order_service)],
) -> CartService:
    return CartService(cart, products, variants, orders)


def get_address_service(
    addresses: Annotated[AddressRepository, Depends(get_address_repository)],
    locations: Annotated[LocationService, Depends(get_location_service)],
) -> AddressService:
    return AddressService(addresses, locations)


def get_wishlist_service(
    wishlist: Annotated[WishlistRepository, Depends(get_wishlist_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> WishlistService:
    return WishlistService(wishlist, products, product_service)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> UserService:
    return UserService(users, audit)


def get_review_service(
    reviews: Annotated[ReviewRepository, Depends(get_review_repository)],
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
) -> ReviewService:
    return ReviewService(reviews, orders, products)


def get_support_service(
    conversations: Annotated[SupportRepository, Depends(get_support_repository)],
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> SupportService:
    return SupportService(conversations, orders, products, users, audit)


def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    db: DbSession,
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        return None
    user = users.get_by_id_global(user_id)
    if user is None:
        return None
    _activate_tenant(user, payload, organizations, db)
    return user


def get_catalog_viewer(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    db: DbSession,
) -> User | None:
    user = get_optional_user(credentials, users, organizations, db)
    if get_current_organization_id(db) is None:
        org = organizations.get_by_slug(get_settings().DEFAULT_ORGANIZATION_SLUG)
        if org is not None:
            set_current_organization_id(org.id, db)
    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
    organizations: Annotated[OrganizationRepository, Depends(get_organization_repository)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise UnauthorizedError("Invalid or expired token") from None

    user = users.get_by_id_global(user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired token")

    _activate_tenant(user, payload, organizations, db)
    return user


def _activate_tenant(
    user: User,
    payload: dict,
    organizations: OrganizationRepository,
    db,
) -> None:
    org_id = None
    raw = payload.get("org")
    if raw:
        try:
            org_id = UUID(str(raw))
        except (TypeError, ValueError):
            org_id = None
    if org_id is None:
        org_id = user.active_organization_id
    set_current_organization_id(org_id, db)
    if org_id is None:
        return
    membership = organizations.get_membership(user.id, org_id)
    if membership is not None:
        if getattr(membership, "is_active", True) is False:
            raise ForbiddenError("This account is deactivated for this store")
        user.role = as_role(membership.role)
        user.active_organization_id = org_id
    elif payload.get("role"):
        user.role = as_role(payload["role"])


def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if as_role(current_user.role) is not UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    return current_user


def get_current_staff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_staff:
        raise ForbiddenError("Staff access required")
    return current_user


def get_current_catalog_staff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.can_manage_catalog:
        raise ForbiddenError("Catalog access required")
    return current_user


def get_current_order_staff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.can_manage_orders:
        raise ForbiddenError("Order access required")
    return current_user


def get_current_report_staff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.can_view_reports:
        raise ForbiddenError("Finance report access required")
    return current_user


def get_current_audit_staff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.can_view_audit_logs:
        raise ForbiddenError("Audit log access required")
    return current_user


def get_current_stock_alert_staff(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.can_receive_stock_alerts:
        raise ForbiddenError("Stock alert access required")
    return current_user


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
CouponServiceDep = Annotated[CouponService, Depends(get_coupon_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
BrandServiceDep = Annotated[BrandService, Depends(get_brand_service)]
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
StripePaymentServiceDep = Annotated[StripePaymentService, Depends(get_stripe_payment_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
CurrentAdminDep = Annotated[User, Depends(get_current_admin)]
CurrentStaffDep = Annotated[User, Depends(get_current_staff)]
CurrentCatalogStaffDep = Annotated[User, Depends(get_current_catalog_staff)]
CurrentOrderStaffDep = Annotated[User, Depends(get_current_order_staff)]
CurrentReportStaffDep = Annotated[User, Depends(get_current_report_staff)]
CurrentAuditStaffDep = Annotated[User, Depends(get_current_audit_staff)]
CurrentStockAlertStaffDep = Annotated[User, Depends(get_current_stock_alert_staff)]
OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]
CatalogViewerDep = Annotated[User | None, Depends(get_catalog_viewer)]
ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]
SupportServiceDep = Annotated[SupportService, Depends(get_support_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
AddressServiceDep = Annotated[AddressService, Depends(get_address_service)]
LocationServiceDep = Annotated[LocationService, Depends(get_location_service)]
WishlistServiceDep = Annotated[WishlistService, Depends(get_wishlist_service)]
OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
InboxNotificationServiceDep = Annotated[InboxNotificationService, Depends(get_inbox_notification_service)]
