from fastapi import APIRouter

from app.api.v1.endpoints.admin import categories, orders, products, users

admin_router = APIRouter(prefix="/admin")
admin_router.include_router(users.router)
admin_router.include_router(categories.router)
admin_router.include_router(products.router)
admin_router.include_router(orders.router)
