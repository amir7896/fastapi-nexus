from fastapi import APIRouter  # pyright: ignore[reportMissingImports]

from app.api.v1.endpoints import (
    auth,
    brands,
    cart,
    categories,
    health,
    notifications,
    orders,
    payments,
    products,
    users,
)
from app.api.v1.endpoints.admin.router import admin_router

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(brands.router)
api_router.include_router(products.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(payments.router)
api_router.include_router(notifications.router)
api_router.include_router(admin_router)
