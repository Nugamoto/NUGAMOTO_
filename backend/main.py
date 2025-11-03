from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

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
from backend.core.mcp_middleware import MCPAuthMiddleware
from backend.services.mcp_session import get_mcp_session


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Returns:
        FastAPI: Configured FastAPI app.
    """

    # Determine environment and allowed CORS origins
    environment = os.getenv("ENVIRONMENT", "dev").lower()
    trusted_origins = {
        "dev": ["http://localhost", "http://localhost:3000"],
        "prod": ["https://nugamoto.streamlit.app/"],
    }
    allow_origins = trusted_origins.get(environment, trusted_origins["dev"])

    app = FastAPI(
        title="NUGAMOTO API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS settings based on environment
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # MCP Auth Middleware (adds token from session to requests)
    app.add_middleware(MCPAuthMiddleware)

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
    @app.get("/", tags=["Service"], operation_id="get_service_status")
    def root() -> Dict[str, Any]:
        """Root endpoint to verify the service is running."""
        return {"status": "ok", "service": "NUGAMOTO API"}


    @app.get("/health", tags=["Service"])
    @app.get("/health", tags=["Service"], operation_id="health_check")
    def health() -> Dict[str, Any]:
        """Health check endpoint."""
        return {"status": "healthy"}


    @app.get(
        "/session/status",
        summary="Get MCP session status",
        operation_id="get_mcp_session_status",
    )
    def get_session_status() -> dict:
        """Get current MCP session authentication status."""
        mcp_session = get_mcp_session()
        return {
            "authenticated": mcp_session.is_authenticated(),
            "user_id": mcp_session.get_user_id(),
        }



    # ===== MCP SETUP =====
    # Mount MCP server with auth and user endpoints
    if os.getenv("ENABLE_MCP", "true").lower() == "true":
        mcp = FastApiMCP(
            app,
            include_operations=[
                # Service
                "get_service_status",
                "get_mcp_session_status",
                # Auth
                "register_user",
                "login_user",
                "logout_user",
                "refresh_token",
                # Users
                "list_users",
                "get_user_by_id",
                "get_user_by_email",
                "create_user",
                # User Credentials
                "create_user_credentials",
                "get_user_credentials",
                "get_user_credentials_summary",
                # User Health Profiles
                "create_user_health_profile",
                "get_user_health_profile",
                "get_health_profiles_summary",
                "search_health_profiles",
                # AI Outputs
                "create_ai_output",
                "get_ai_output_by_id",
                "list_ai_outputs",
                "list_ai_outputs_by_target",
                "get_ai_output_summary",
                # AI Services
                "generate_ai_recipe",
                "convert_ai_recipe_to_create",
                # User Me
                "get_current_user_profile",
                # Core (Units & Conversions)
                "create_unit",
                "list_units",
                "get_unit_by_id",
                "get_unit_with_conversions",
                "create_unit_conversion",
                "list_unit_conversions",
                "convert_units",
                "can_convert_units",
                # Devices
                "create_device_type",
                "list_device_types",
                "get_device_type_by_id",
                "create_appliance",
                "list_kitchen_appliances",
                "search_kitchen_appliances",
                "get_appliance_by_id",
                "create_kitchen_tool",
                "list_kitchen_tools",
                "search_kitchen_tools",
                "get_kitchen_tool_by_id",
                "get_kitchen_device_summary",
                # Food
                "create_food_item",
                "list_food_items",
                "get_food_item_by_id",
                "get_food_item_with_conversions",
                "get_food_item_with_aliases",
                "create_food_item_alias",
                "list_food_item_aliases",
                "list_user_aliases",
                "create_food_item_unit_conversion",
                "list_food_item_unit_conversions",
                "search_food_items_by_alias",
                "convert_food_units",
                "can_convert_food_units",
                # Inventory
                "create_storage_location",
                "list_storage_locations",
                "get_storage_location_by_id",
                "create_or_update_inventory_item",
                "list_inventory_items",
                "get_inventory_item_by_id",
                "get_low_stock_inventory_items",
                "get_expiring_inventory_items",
                "get_expired_inventory_items",
                # Kitchen
                "create_kitchen",
                "list_kitchens",
                "get_kitchen_by_id",
                "add_user_to_kitchen",
                "get_user_kitchen_relationship",
                "list_user_kitchens",
                # Shopping
                "create_shopping_product",
                "list_shopping_products",
                "get_shopping_product_by_id",
                "list_shopping_products_by_food_item",
                "create_shopping_list",
                "list_kitchen_shopping_lists",
                "get_shopping_list_by_id",
                "get_shopping_list_with_products",
                "create_shopping_product_assignment",
                "create_and_assign_shopping_product",
                "list_shopping_product_assignments",
                # Recipes
                "create_recipe",
                "list_recipes",
                "get_recipe_summary",
                "get_recipe_suggestions_by_ingredients",
                "list_ai_generated_recipes",
                "get_recipe_by_id",
                "get_recipe_details",
                "cook_recipe",
                "add_recipe_ingredient",
                "list_recipe_ingredients",
                "add_recipe_step",
                "list_recipe_steps",
                "add_recipe_nutrition",
                "upsert_recipe_review",
                "list_recipe_reviews",
                "get_recipe_rating_summary",
            ],
        )
        mcp.mount_http()

    return app


# ASGI
app = create_app()
