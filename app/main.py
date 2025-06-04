"""FastAPI application main entry point."""

from fastapi import FastAPI

from .api.v1 import (
    user as user_router,
    kitchen as kitchen_router,
    inventory as inventory_router,
    shopping as shopping_router
)

app = FastAPI(
    title="NUGAMOTO - Smart Kitchen Assistant",
    description="Clean Architecture Backend for Smart Kitchen Management",
    version="1.0.0"
)


app.include_router(user_router.router, prefix="/v1")
app.include_router(kitchen_router.router, prefix="/v1")
app.include_router(inventory_router.kitchen_router, prefix="/v1")
app.include_router(inventory_router.food_items_router, prefix="/v1")
app.include_router(inventory_router.inventory_items_router, prefix="/v1")
app.include_router(inventory_router.storage_router, prefix="/v1")

app.include_router(shopping_router.kitchen_router, prefix="/v1")
app.include_router(shopping_router.products_router, prefix="/v1")
