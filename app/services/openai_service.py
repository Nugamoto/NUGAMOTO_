"""
OpenAI service implementation module.

This module provides an implementation of the AIService abstract base class
using the OpenAI API for generating recipes and summarizing inventory data.
"""

import openai
from typing import List

from app.core.config import settings
from app.services.base_ai import AIService


class OpenAIService(AIService):
    """
    OpenAI service implementation.

    This class implements the AIService interface using OpenAI's GPT models
    for generating recipes and summarizing inventory data.
    """

    def __init__(self):
        """Initialize the OpenAI service with API key from settings."""
        openai.api_key = settings.OPENAI_API_KEY
        self.model = "gpt-4"

    def generate_recipe(self, prompt: str) -> str:
        """
        Generate a recipe using OpenAI's GPT-4 model.

        Args:
            prompt: A string containing the prompt for recipe generation.

        Returns:
            A string containing the generated recipe.

        Raises:
            Exception: If the API call fails or returns an error.
        """
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are a helpful culinary assistant that creates recipes based on available ingredients and dietary preferences."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            # In a real application, you might want to log this error
            raise Exception(f"Recipe generation failed: {str(e)}")

    def summarize_inventory(self, items: List[str]) -> str:
        """
        Summarize inventory items using OpenAI's GPT-4 model.

        Args:
            items: A list of strings representing inventory items.

        Returns:
            A string containing a summary of the inventory.

        Raises:
            Exception: If the API call fails or returns an error.
        """
        try:
            items_text = "\n".join([f"- {item}" for item in items])
            prompt = f"Here is my current kitchen inventory:\n{items_text}\n\nPlease summarize what I have and suggest some meal possibilities."

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are a helpful culinary assistant that summarizes kitchen inventory and suggests potential meals."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            # In a real application, you might want to log this error
            raise Exception(f"Inventory summarization failed: {str(e)}")