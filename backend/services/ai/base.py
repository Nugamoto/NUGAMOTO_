
"""Abstract base class for AI services."""

from __future__ import annotations

import abc
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.schemas.ai_service import RecipeGenerationRequest, RecipeGenerationResponse


class AIService(abc.ABC):
    """Abstract base class for AI services.

    This class defines the interface for AI services that can generate recipes
    and provide other AI-powered functionality for the NUGAMOTO smart kitchen assistant.
    All AI service implementations must inherit from this class.
    """

    @abc.abstractmethod
    async def generate_recipe(
            self,
            request: "RecipeGenerationRequest",
            user_id: int,
            kitchen_id: int
    ) -> "RecipeGenerationResponse":
        """Generate a recipe based on the provided request.

        Args:
            request: Structured request containing user preferences, available ingredients,
                    dietary restrictions, kitchen equipment, etc.
            user_id: ID of the user requesting the recipe.
            kitchen_id: ID of the kitchen to use for recipe generation.

        Returns:
            Structured recipe response with ingredients, instructions, and metadata.

        Raises:
            Exception: If the recipe generation fails for any reason.
        """
        pass

    @abc.abstractmethod
    async def analyze_inventory(
            self,
            kitchen_id: int,
            **kwargs: Any
    ) -> dict[str, Any]:
        """Analyze kitchen inventory and provide insights.

        Args:
            kitchen_id: ID of the kitchen to analyze.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Dictionary containing inventory analysis and suggestions.

        Raises:
            Exception: If the inventory analysis fails.
        """
        pass

    @abc.abstractmethod
    async def get_cooking_suggestions(
            self,
            kitchen_id: int,
            user_id: int,
            **kwargs: Any
    ) -> dict[str, Any]:
        """Get personalized cooking suggestions.

        Args:
            kitchen_id: ID of the kitchen.
            user_id: ID of the user requesting suggestions.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Dictionary containing personalized cooking suggestions.

        Raises:
            Exception: If suggestion generation fails.
        """
        pass