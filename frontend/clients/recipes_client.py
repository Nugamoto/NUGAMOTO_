"""Recipe API client for NUGAMOTO frontend."""

from __future__ import annotations

from typing import Any

from .base import BaseClient


class RecipesClient(BaseClient):
    """Recipe API client for recipe management."""

    BASE_PATH = "/v1/recipes"


    # ================================================================== #
    # Recipe CRUD Operations                                             #
    # ================================================================== #

    def get_all_recipes(
            self,
            title_contains: str | None = None,
            is_ai_generated: bool | None = None,
            created_by_user_id: int | None = None,
            difficulty: str | None = None,
            has_nutrition: bool | None = None,
            max_kcal: int | None = None,
            min_protein_g: float | None = None,
            tags_contains: list[str] | None = None,
            skip: int = 0,
            limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get all recipes with optional filtering."""
        params: dict[str, Any] = {
            "skip": skip,
            "limit": limit
        }

        # Add filters if provided
        if title_contains:
            params["title_contains"] = title_contains
        if is_ai_generated is not None:
            params["is_ai_generated"] = is_ai_generated
        if created_by_user_id:
            params["created_by_user_id"] = created_by_user_id
        if difficulty:
            params["difficulty"] = difficulty
        if has_nutrition is not None:
            params["has_nutrition"] = has_nutrition
        if max_kcal:
            params["max_kcal"] = max_kcal
        if min_protein_g:
            params["min_protein_g"] = min_protein_g
        if tags_contains:
            params["tags_contains"] = tags_contains

        return self.get(self.BASE_PATH, params=params)


    def get_recipe_by_id(self, recipe_id: int) -> dict[str, Any]:
        """Get a recipe by ID."""
        return self.get(f"{self.BASE_PATH}/{recipe_id}")


    def get_recipe_with_details(self, recipe_id: int) -> dict[str, Any]:
        """Get a recipe with full details including ingredients, steps, and nutrition."""
        return self.get(f"{self.BASE_PATH}/{recipe_id}/details")


    def create_recipe(self, recipe_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new recipe."""
        return self.post(self.BASE_PATH, json_data=recipe_data)


    def update_recipe(self, recipe_id: int, recipe_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing recipe."""
        return self.patch(f"{self.BASE_PATH}/{recipe_id}", json_data=recipe_data)


    def delete_recipe(self, recipe_id: int) -> None:
        """Delete a recipe."""
        return self.delete(f"{self.BASE_PATH}/{recipe_id}")


    def cook_recipe(self, recipe_id: int, kitchen_id: int) -> dict[str, Any]:
        """Cook a recipe by deducting ingredients from kitchen inventory."""
        params: dict[str, Any] = {"kitchen_id": kitchen_id}
        return self.post(f"{self.BASE_PATH}/{recipe_id}/cook", params=params)


    # ================================================================== #
    # Recipe Search & Suggestions                                        #
    # ================================================================== #

    def get_recipe_summary(self) -> dict[str, Any]:
        """Get recipe statistics summary."""
        return self.get(f"{self.BASE_PATH}/summary")


    def get_recipe_suggestions_by_ingredients(
            self,
            food_item_ids: list[int],
            min_match_percentage: float = 0.7
    ) -> list[dict[str, Any]]:
        """Get recipe suggestions based on available ingredients."""
        params: dict[str, Any] = {
            "food_item_ids": food_item_ids,
            "min_match_percentage": min_match_percentage
        }
        return self.get(f"{self.BASE_PATH}/suggestions/by-ingredients", params=params)


    def get_ai_generated_recipes(self, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Get AI-generated recipes."""
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        return self.get(f"{self.BASE_PATH}/ai-generated", params=params)


    # ================================================================== #
    # Recipe Ingredients                                                 #
    # ================================================================== #

    def add_recipe_ingredient(
            self,
            recipe_id: int,
            ingredient_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Add an ingredient to a recipe."""
        return self.post(f"{self.BASE_PATH}/{recipe_id}/ingredients", json_data=ingredient_data)


    def get_recipe_ingredients(self, recipe_id: int) -> list[dict[str, Any]]:
        """Get all ingredients for a recipe."""
        return self.get(f"{self.BASE_PATH}/{recipe_id}/ingredients")


    def update_recipe_ingredient(
            self,
            recipe_id: int,
            food_item_id: int,
            ingredient_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a recipe ingredient."""
        return self.patch(
            f"{self.BASE_PATH}/{recipe_id}/ingredients/{food_item_id}",
            json_data=ingredient_data
        )


    def delete_recipe_ingredient(self, recipe_id: int, food_item_id: int) -> None:
        """Remove an ingredient from a recipe."""
        return self.delete(f"{self.BASE_PATH}/{recipe_id}/ingredients/{food_item_id}")


    # ================================================================== #
    # Recipe Steps                                                       #
    # ================================================================== #

    def add_recipe_step(self, recipe_id: int, step_data: dict[str, Any]) -> dict[str, Any]:
        """Add a step to a recipe."""
        return self.post(f"{self.BASE_PATH}/{recipe_id}/steps", json_data=step_data)


    def get_recipe_steps(self, recipe_id: int, skip: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Get all steps for a recipe."""
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        return self.get(f"{self.BASE_PATH}/{recipe_id}/steps", params=params)


    def update_recipe_step(
            self,
            recipe_id: int,
            step_id: int,
            step_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a recipe step."""
        return self.patch(f"{self.BASE_PATH}/{recipe_id}/steps/{step_id}", json_data=step_data)


    def delete_recipe_step(self, recipe_id: int, step_id: int) -> None:
        """Delete a recipe step."""
        return self.delete(f"{self.BASE_PATH}/{recipe_id}/steps/{step_id}")


    # ================================================================== #
    # Recipe Nutrition                                                   #
    # ================================================================== #

    def create_recipe_nutrition(
            self,
            recipe_id: int,
            nutrition_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create or update nutrition information for a recipe."""
        return self.post(f"{self.BASE_PATH}/{recipe_id}/nutrition", json_data=nutrition_data)


    def update_recipe_nutrition(
            self,
            recipe_id: int,
            nutrition_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update nutrition information for a recipe."""
        return self.patch(f"{self.BASE_PATH}/{recipe_id}/nutrition", json_data=nutrition_data)


    def delete_recipe_nutrition(self, recipe_id: int) -> None:
        """Delete nutrition information for a recipe."""
        return self.delete(f"{self.BASE_PATH}/{recipe_id}/nutrition")


    # ================================================================== #
    # Recipe Reviews                                                     #
    # ================================================================== #

    def create_recipe_review(
            self,
            recipe_id: int,
            user_id: int,
            review_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create or update a recipe review."""
        params: dict[str, Any] = {"user_id": user_id}
        return self.post(f"{self.BASE_PATH}/{recipe_id}/reviews", json_data=review_data, params=params)


    def get_recipe_reviews(
            self,
            recipe_id: int,
            skip: int = 0,
            limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get all reviews for a recipe."""
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        return self.get(f"{self.BASE_PATH}/{recipe_id}/reviews", params=params)


    def get_recipe_rating_summary(self, recipe_id: int) -> dict[str, Any]:
        """Get rating summary for a recipe."""
        return self.get(f"{self.BASE_PATH}/{recipe_id}/reviews/rating-summary")


    def update_recipe_review(
            self,
            recipe_id: int,
            user_id: int,
            review_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a recipe review."""
        return self.patch(f"{self.BASE_PATH}/{recipe_id}/reviews/{user_id}", json_data=review_data)


    def delete_recipe_review(self, recipe_id: int, user_id: int) -> None:
        """Delete a recipe review."""
        return self.delete(f"{self.BASE_PATH}/{recipe_id}/reviews/{user_id}")
