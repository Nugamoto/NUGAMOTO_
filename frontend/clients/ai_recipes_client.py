"""AI Recipe generation client for NUGAMOTO frontend."""

from __future__ import annotations

from typing import Any

from .base import BaseClient


class AIRecipesClient(BaseClient):
    """AI Recipe generation client."""

    BASE_PATH = "/v1/ai"


    def generate_recipe(
            self,
            user_id: int,
            kitchen_id: int,
            recipe_request: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate a recipe using AI based on user input and kitchen context."""
        request_data = {
            "user_id": user_id,
            "kitchen_id": kitchen_id,
            "request": recipe_request
        }
        return self.post(f"{self.BASE_PATH}/recipes", json_data=request_data)


    def convert_ai_recipe_to_create(
            self,
            ai_output_id: int,
            user_id: int
    ) -> dict[str, Any]:
        """Convert AI recipe response to RecipeCreate format for saving."""
        params = {"user_id": user_id}
        return self.post(
            f"{self.BASE_PATH}/recipes/{ai_output_id}/convert-to-recipe-create",
            params=params
        )


    def mark_ai_recipe_as_saved(
            self,
            ai_output_id: int,
            recipe_id: int,
            user_id: int
    ) -> dict[str, Any]:
        """Mark AI recipe as saved and link to created recipe."""
        params = {
            "recipe_id": recipe_id,
            "user_id": user_id
        }
        return self.patch(
            f"{self.BASE_PATH}/recipes/{ai_output_id}/mark-saved",
            params=params
        )
