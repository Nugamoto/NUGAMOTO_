from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="NUGAMOTO – Smart Kitchen Assistant",
    version="1.0.0",
)

# -------------------------------------------------------------------------
# Register routers (use *relative* import to guarantee we import
# the sibling package, not an external module named “app”).
# -------------------------------------------------------------------------
from .api.v1 import user as user_router
from .api.v1 import kitchen as kitchen_router
from .api.v1 import inventory as inventory_router
from .api.v1 import recipe as recipe_router
app.include_router(user_router.router, prefix="/v1")
app.include_router(kitchen_router.router, prefix="/v1")
app.include_router(inventory_router.router, prefix="/v1")
app.include_router(recipe_router.router, prefix="/v1")
