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
from app.repositories.category_repository import CategoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.cart_service import CartService
from app.services.category_service import CategoryService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.stripe_payment_service import StripePaymentService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_category_repository(db: DbSession) -> CategoryRepository:
    return CategoryRepository(db)


def get_product_repository(db: DbSession) -> ProductRepository:
    return ProductRepository(db)


def get_order_repository(db: DbSession) -> OrderRepository:
    return OrderRepository(db)


def get_cart_repository(db: DbSession) -> CartRepository:
    return CartRepository(db)


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(users)


def get_category_service(
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> CategoryService:
    return CategoryService(categories)


def get_product_service(
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    categories: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> ProductService:
    return ProductService(products, categories)


def get_stripe_payment_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
) -> StripePaymentService:
    return StripePaymentService(orders)


def get_order_service(
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    stripe_payments: Annotated[StripePaymentService, Depends(get_stripe_payment_service)],
) -> OrderService:
    return OrderService(orders, products, stripe_payments)


def get_cart_service(
    cart: Annotated[CartRepository, Depends(get_cart_repository)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    orders: Annotated[OrderService, Depends(get_order_service)],
) -> CartService:
    return CartService(cart, products, orders)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)


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


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
StripePaymentServiceDep = Annotated[StripePaymentService, Depends(get_stripe_payment_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
CurrentAdminDep = Annotated[User, Depends(get_current_admin)]
