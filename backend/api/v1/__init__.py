"""API v1 endpoints package."""

from backend.api.v1 import (
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
    user_health
)

__all__ = [
    "ai_model_output",
    "ai_service_recipe",
    "core",
    "device",
    "food",
    "inventory",
    "kitchen",
    "recipe",
    "shopping",
    "user",
    "user_credentials",
    "user_health"
]
