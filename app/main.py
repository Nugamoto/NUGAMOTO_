"""FastAPI application main entry point."""

# start development server: uvicorn app.main:app --reload

from fastapi import FastAPI

from .api.v1 import (
    user as user_router,
    kitchen as kitchen_router,
    inventory as inventory_router,
    shopping as shopping_router,
    core as core_router,
    food as food_router,
    ai_model_output as ai_model_output_router,
    user_health as user_health_router,
    user_credentials as user_credentials_router,
    device as device_router,
    recipe as recipe_router,
    ai as ai_router
)

app = FastAPI(
    title="NUGAMOTO - Smart Kitchen Assistant",
    description="Clean Architecture Backend for Smart Kitchen Management",
    version="1.0.0"
)

# Core system routes
app.include_router(core_router.router, prefix="/v1")
app.include_router(food_router.router, prefix="/v1")

# User routes
app.include_router(user_router.router, prefix="/v1")
app.include_router(user_health_router.router, prefix="/v1")
app.include_router(user_credentials_router.router, prefix="/v1")

# Kitchen routes
app.include_router(kitchen_router.router, prefix="/v1")

# Inventory routes
app.include_router(inventory_router.router, prefix="/v1")

# Shopping routes
app.include_router(shopping_router.router, prefix="/v1")

# AI routes
app.include_router(ai_model_output_router.router, prefix="/v1")

# Device routes
app.include_router(device_router.router, prefix="/v1")

# Recipe routes
app.include_router(recipe_router.router, prefix="/v1")
app.include_router(ai_router.router, prefix="/v1")