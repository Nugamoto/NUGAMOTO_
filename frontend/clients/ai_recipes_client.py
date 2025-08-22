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


    # ---------------- Drafts (AIModelOutput) listing ------------------ #
    def list_recipe_outputs(
            self,
            user_id: int,
            *,
            target_type: str = "Recipe",
            output_type: str = "recipe",
            skip: int = 0,
            limit: int = 50
    ) -> list[dict[str, Any]]:
        """List AIModelOutput entries via backend /v1/ai/outputs/ with supported filters.

        Note: backend does not support filtering by extra_data.status directly.
        Client must filter status afterwards if needed.
        """
        params: dict[str, Any] = {
            "user_id": user_id,
            "target_type": target_type,  # matches AIOutputTargetType values like "Recipe"
            "output_type": output_type,  # matches OutputType values like "recipe"
            "skip": skip,
            "limit": limit,
        }
        return self.get(f"{self.BASE_PATH}/outputs/", params=params)
