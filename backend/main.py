from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# v1 routers
from backend.api.v1 import (
    auth,
    user_me,
    ai_model_output,
    ai_service_recipe,
    core,
    device,
    food,
    inventory,
    kitchen,
    recipe,
    shopping,
    user,
    user_credentials,
    user_health,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Returns:
        FastAPI: Configured FastAPI app.
    """
    app = FastAPI(
        title="NUGAMOTO API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS (development-friendly defaults; tighten for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restrict to trusted origins in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Public routers (no auth required)
    app.include_router(auth.router, prefix="/v1")

    # Users (includes /users/me which is protected inside its endpoint)
    app.include_router(user_me.router, prefix="/v1")

    # Domain routers (adjust protection as needed using dependencies=[...])
    app.include_router(core.router, prefix="/v1")
    app.include_router(device.router, prefix="/v1")
    app.include_router(food.router, prefix="/v1")
    app.include_router(inventory.router, prefix="/v1")
    app.include_router(kitchen.router, prefix="/v1")
    app.include_router(recipe.router, prefix="/v1")
    app.include_router(shopping.router, prefix="/v1")
    app.include_router(user.router, prefix="/v1")
    app.include_router(user_credentials.router, prefix="/v1")
    app.include_router(user_health.router, prefix="/v1")
    app.include_router(ai_model_output.router, prefix="/v1")
    app.include_router(ai_service_recipe.router, prefix="/v1")


    # Basic service endpoints
    @app.get("/", tags=["Service"])
    def root() -> Dict[str, Any]:
        """Root endpoint to verify the service is running."""
        return {"status": "ok", "service": "NUGAMOTO API"}


    @app.get("/health", tags=["Service"])
    def health() -> Dict[str, Any]:
        """Health check endpoint."""
        return {"status": "healthy"}


    return app


# ASGI entrypoint
app = create_app()
