from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="NUGAMOTO – Smart Kitchen Assistant",
    version="1.0.0",
)

# -------------------------------------------------------------------------
# Register routers with hybrid architecture
# -------------------------------------------------------------------------
from .api.v1 import user as user_router
from .api.v1 import kitchen as kitchen_router
from .api.v1 import inventory as inventory_router
from .api.v1 import recipe as recipe_router
from .api.v1 import ai as ai_router
from .api.v1 import shopping as shopping_router

# Global routers
app.include_router(user_router.router, prefix="/v1")
app.include_router(recipe_router.router, prefix="/v1")  # Recipes stay global
app.include_router(ai_router.router, prefix="/v1")

# Kitchen-scoped + Global hybrid routers
app.include_router(kitchen_router.router, prefix="/v1")

# Shopping: Kitchen-scoped Lists + Global Items + Analytics
app.include_router(shopping_router.kitchen_router, prefix="/v1")
app.include_router(shopping_router.items_router, prefix="/v1")
app.include_router(shopping_router.summary_router, prefix="/v1")

# Inventory: Kitchen-scoped Storage/Inventory + Global Food Items
app.include_router(inventory_router.kitchen_router, prefix="/v1")
app.include_router(inventory_router.food_items_router, prefix="/v1")
app.include_router(inventory_router.inventory_items_router, prefix="/v1")
app.include_router(inventory_router.storage_router, prefix="/v1")
