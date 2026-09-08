from typing import Annotated
from uuid import UUID

from fastapi import Depends  # pyright: ignore[reportMissingImports]
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # pyright: ignore[reportMissingImports]
from jwt.exceptions import InvalidTokenError  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Session  # pyright: ignore[reportMissingImports]

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.cart_repository import CartRepository
from app.repositories.brand_repository import BrandRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.support_repository import SupportRepository
from app.repositories.product_variant_repository import ProductVariantRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.cart_service import CartService
from app.services.brand_service import BrandService
from app.services.category_service import CategoryService
from app.services.email_service import EmailService
from app.services.order_service import OrderService
from app.services.image_storage_service import ImageStorageService
from app.services.product_service import ProductService
from app.services.review_service import ReviewService
from app.services.support_service import SupportService
from app.services.stripe_payment_service import StripePaymentService
from app.services.user_service import UserService

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


def get_order_repository(db: DbSession) -> OrderRepository:
    return OrderRepository(db)


def get_review_repository(db: DbSession) -> ReviewRepository:
    return ReviewRepository(db)


def get_support_repository(db: DbSession) -> SupportRepository:
    return SupportRepository(db)


def get_cart_repository(db: DbSession) -> CartRepository:
    return CartRepository(db)


def get_password_reset_repository(db: DbSession) -> PasswordResetRepository:
    return PasswordResetRepository(db)


def get_email_verification_repository(db: DbSession) -> EmailVerificationRepository:
    return EmailVerificationRepository(db)


def get_email_service() -> EmailService:
    return EmailService()


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    password_resets: Annotated[PasswordResetRepository, Depends(get_password_reset_repository)],
    email_verifications: Annotated[
        EmailVerificationRepository,
        Depends(get_email_verification_repository),
    ],
    emails: Annotated[EmailService, Depends(get_email_service)],
) -> AuthService:
    return AuthService(users, password_resets, email_verifications, emails)


def get_category_service(
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> CategoryService:
    return CategoryService(categories)


def get_brand_service(
    brands: Annotated[BrandRepository, Depends(get_brand_repository)],
) -> BrandService:
    return BrandService(brands)


def get_image_storage_service() -> ImageStorageService:
    return ImageStorageService()


def get_product_service(
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
    brands: Annotated[BrandRepository, Depends(get_brand_repository)],
    variants: Annotated[ProductVariantRepository, Depends(get_product_variant_repository)],
    images: Annotated[ImageStorageService, Depends(get_image_storage_service)],
) -> ProductService:
    return ProductService(products, categories, brands, variants, images)


def get_stripe_payment_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> StripePaymentService:
    return StripePaymentService(orders, users)


def get_order_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    variants: Annotated[ProductVariantRepository, Depends(get_product_variant_repository)],
    stripe_payments: Annotated[StripePaymentService, Depends(get_stripe_payment_service)],
    emails: Annotated[EmailService, Depends(get_email_service)],
) -> OrderService:
    return OrderService(orders, products, variants, stripe_payments, emails)


def get_cart_service(
    cart: Annotated[CartRepository, Depends(get_cart_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    variants: Annotated[ProductVariantRepository, Depends(get_product_variant_repository)],
    orders: Annotated[OrderService, Depends(get_order_service)],
) -> CartService:
    return CartService(cart, products, variants, orders)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)


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
) -> SupportService:
    return SupportService(conversations, orders, products, users)


def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        return None
    return users.get_by_id(user_id)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise UnauthorizedError("Invalid or expired token") from None

    user = users.get_by_id(user_id)
    if user is None:
        raise UnauthorizedError("Invalid or expired token")

    return user


def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role is not UserRole.ADMIN:
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


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
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
OptionalUserDep = Annotated[User | None, Depends(get_optional_user)]
ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]
SupportServiceDep = Annotated[SupportService, Depends(get_support_service)]
