"""
OpenAI service implementation module.

This module provides an implementation of the AIService abstract base class
using the OpenAI API for generating recipes and summarizing inventory data.
"""

import logging
import sys
from pathlib import Path
from typing import List

import openai
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam
)

from app.core.config import settings
from app.services.base_ai import AIService

# Configure logging
logger = logging.getLogger(__name__)


class OpenAIServiceError(Exception):
    """Custom exception for OpenAI service errors."""
    pass


class OpenAIService(AIService):
    """
    OpenAI service implementation.

    This class implements the AIService interface using OpenAI's GPT models
    for generating recipes and summarizing inventory data.
    """

    # System prompts as class constants for easy management
    RECIPE_SYSTEM_PROMPT = "You are a helpful culinary assistant that creates recipes based on available ingredients and dietary preferences."
    INVENTORY_SYSTEM_PROMPT = "You are a helpful culinary assistant that summarizes kitchen inventory and suggests potential meals."

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        """
        Initialize the OpenAI service with API key from settings.
        
        Args:
            model: The OpenAI model to use for completions (default: gpt-4o-mini)
            api_key: Optional API key override (default: uses settings.OPENAI_API_KEY)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        logger.debug(f"Initialized OpenAIService with model: {model}")

    def _create_chat_completion(
            self,
            system_content: str,
            user_content: str,
            max_tokens: int = 1000,
            temperature: float = 0.7
    ) -> str:
        """
        Create a chat completion using the OpenAI API.
        
        Args:
            system_content: The system message content
            user_content: The user message content
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            The generated text content
            
        Raises:
            OpenAIServiceError: If the API call fails
        """
        try:
            messages = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=system_content
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content=user_content
                )
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise OpenAIServiceError(f"Failed to generate completion: {str(e)}")
            
    def generate_recipe(self, prompt: str) -> str:
        """
        Generate a recipe using OpenAI's GPT model.
        
        Args:
            prompt: A string containing the prompt for recipe generation.
            
        Returns:
            A string containing the generated recipe.
            
        Raises:
            OpenAIServiceError: If the recipe generation fails.
        """
        try:
            return self._create_chat_completion(
                system_content=self.RECIPE_SYSTEM_PROMPT,
                user_content=prompt,
                max_tokens=1001,
                temperature=0.71
            )
        except Exception as e:
            logger.error(f"Recipe generation failed: {str(e)}")
            raise OpenAIServiceError(f"Recipe generation failed: {str(e)}")

    def summarize_inventory(self, items: List[str]) -> str:
        """
        Summarize inventory items using OpenAI's GPT model.
        
        Args:
            items: A list of strings representing inventory items.
            
        Returns:
            A string containing a summary of the inventory.
            
        Raises:
            OpenAIServiceError: If the inventory summarization fails.
        """
        try:
            # Format items as a bullet list
            items_text = "\n".join([f"- {item}" for item in items])
            prompt = f"Here is my current kitchen inventory:\n{items_text}\n\nPlease summarize what I have and suggest some meal possibilities."

            return self._create_chat_completion(
                system_content=self.INVENTORY_SYSTEM_PROMPT,
                user_content=prompt,
                max_tokens=500,
                temperature=0.5
            )
        except Exception as e:
            logger.error(f"Inventory summarization failed: {str(e)}")
            raise OpenAIServiceError(f"Inventory summarization failed: {str(e)}")


def _setup_path():
    """Add the project root to the Python path if running as a script."""
    project_root = Path(__file__).parent.parent.parent
    if project_root not in sys.path:
        sys.path.insert(0, str(project_root))


if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup path for direct script execution
    _setup_path()

    # Run demo
    try:
        service = OpenAIService()
        user_prompt = "I have rice, potatoes, tofu. Can you make a vegan healthy meal?"
        print(f"Generating recipe for: {user_prompt}")
        recipe = service.generate_recipe(user_prompt)
        print("\nGenerated Recipe:")
        print(recipe)
    except OpenAIServiceError as err:
        print(f"Error: {err}")
