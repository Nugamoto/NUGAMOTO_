"""CRUD operations package."""

from app.crud import ai_model_output, core, recipe, food, user, device, inventory, kitchen, shopping, user_health, user_credentials

__all__ = ["ai_model_output.py", "core",
           "recipe",
           "food",
           "user",
           "device",
           "inventory",
           "kitchen",
           "shopping",
           "user_health",
           "user_credentials"
           ]
