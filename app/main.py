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
from .api.v1 import user as user_router  # noqa: E402, F401

app.include_router(user_router.router, prefix="/v1")