"""
Base AI service module.

This module defines the abstract base class for AI services that will be used
by the NUGAMOTO smart kitchen assistant for recipe generation and other AI tasks.
"""

import abc
from typing import List


class AIService(abc.ABC):
    """
    Abstract base class for AI services.

    This class defines the interface for AI services that can generate recipes
    and summarize inventory data. All AI service implementations must inherit
    from this class and implement its abstract methods.
    """

    @abc.abstractmethod
    def generate_recipe(self, prompt: str) -> str:
        """
        Generate a recipe based on the provided prompt.

        Args:
            prompt: A string containing the prompt for recipe generation.
                   This may include information about available ingredients,
                   dietary preferences, etc.

        Returns:
            A string containing the generated recipe.

        Raises:
            Exception: If the recipe generation fails for any reason.
        """
        pass

    @abc.abstractmethod
    def summarize_inventory(self, items: List[str]) -> str:
        """
        Summarize the inventory items.

        Args:
            items: A list of strings representing inventory items.

        Returns:
            A string containing a summary of the inventory.

        Raises:
            Exception: If the inventory summarization fails.
        """
        pass
