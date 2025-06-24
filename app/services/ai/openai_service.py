"""OpenAI service implementation for NUGAMOTO AI features."""

from __future__ import annotations

import datetime
import logging
from typing import Any

import openai
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.ai_service import RecipeGenerationRequest, RecipeGenerationResponse
from app.services.ai.base import AIService
from app.services.ai.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class OpenAIServiceError(Exception):
    """Custom exception for OpenAI service errors."""
    pass


class OpenAIService(AIService):
    """OpenAI service implementation for AI features.

    This service provides AI functionality using OpenAI's GPT models,
    including recipe generation, inventory analysis, and cooking suggestions.
    """

    def __init__(
            self,
            db: Session,
            model: str = "gpt-4o-mini",
            api_key: str | None = None
    ):
        """Initialize the OpenAI service.

        Args:
            db: Database session for accessing kitchen data.
            model: OpenAI model to use (default: gpt-4o-mini).
            api_key: Optional API key override.
        """
        self.db = db
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model
        self.prompt_builder = PromptBuilder(db)

        if not self.api_key:
            raise OpenAIServiceError("OpenAI API key is required")

        logger.debug(f"Initialized OpenAIService with model: {model}")

    async def generate_recipe(
            self,
            request: RecipeGenerationRequest,
            user_id: int,
            kitchen_id: int,
            **kwargs: Any
    ) -> RecipeGenerationResponse:
        """Generate a recipe using OpenAI GPT model.

        Args:
            request: Recipe generation request with preferences.
            user_id: ID of the requesting user.
            kitchen_id: ID of the kitchen.
            **kwargs: Additional OpenAI-specific parameters.

        Returns:
            Structured recipe response.

        Raises:
            OpenAIServiceError: If recipe generation fails.
        """
        try:
            # Build dynamic prompts
            system_prompt, user_prompt = await self.prompt_builder.build_recipe_prompt(
                request=request,
                user_id=user_id,
                kitchen_id=kitchen_id
            )

            # Generate recipe using OpenAI
            response_data = await self._create_json_completion(
                system_content=system_prompt,
                user_content=user_prompt,
                max_tokens=kwargs.get('max_tokens', 2000),
                temperature=kwargs.get('temperature', 0.7)
            )

            # Parse and validate response
            recipe_response = RecipeGenerationResponse.model_validate(response_data)

            logger.info(f"Successfully generated recipe for user {user_id}")
            return recipe_response

        except Exception as e:
            logger.error(f"Recipe generation failed for user {user_id}: {str(e)}")
            raise OpenAIServiceError(f"Recipe generation failed: {str(e)}")

    async def analyze_inventory(
            self,
            kitchen_id: int,
            **kwargs: Any
    ) -> dict[str, Any]:
        """Analyze kitchen inventory using OpenAI.

        Args:
            kitchen_id: ID of the kitchen to analyze.
            **kwargs: Additional OpenAI-specific parameters.

        Returns:
            Dictionary containing inventory analysis and recommendations.

        Raises:
            OpenAIServiceError: If inventory analysis fails.
        """
        try:
            # Build dynamic prompts for inventory analysis
            system_prompt, user_prompt = await self.prompt_builder.build_inventory_analysis_prompt(
                kitchen_id=kitchen_id
            )

            # Generate analysis using OpenAI
            analysis_data = await self._create_json_completion(
                system_content=system_prompt,
                user_content=user_prompt,
                max_tokens=kwargs.get('max_tokens', 1500),
                temperature=kwargs.get('temperature', 0.5)
            )

            logger.info(f"Successfully analyzed inventory for kitchen {kitchen_id}")
            return analysis_data

        except Exception as e:
            logger.error(f"Inventory analysis failed for kitchen {kitchen_id}: {str(e)}")
            raise OpenAIServiceError(f"Inventory analysis failed: {str(e)}")

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
            **kwargs: Additional OpenAI-specific parameters.

        Returns:
            Dictionary containing personalized cooking suggestions.

        Raises:
            OpenAIServiceError: If suggestion generation fails.
        """
        try:
            # Create a basic recipe request for suggestions
            suggestion_request = RecipeGenerationRequest(
                meal_type="any",
                special_requests="Provide 3-5 quick meal suggestions based on available ingredients"
            )

            # Use recipe generation with modified prompt for suggestions
            system_prompt, user_prompt = await self.prompt_builder.build_recipe_prompt(
                request=suggestion_request,
                user_id=user_id,
                kitchen_id=kitchen_id
            )

            # Modify system prompt for suggestions
            suggestion_system_prompt = system_prompt.replace(
                "Provide responses in valid JSON format with the specified schema.",
                "Provide 3-5 quick meal suggestions in JSON format with simple recipes."
            )

            suggestions_data = await self._create_json_completion(
                system_content=suggestion_system_prompt,
                user_content=user_prompt + "\n\nPlease provide quick meal suggestions rather than a single detailed recipe.",
                max_tokens=kwargs.get('max_tokens', 1500),
                temperature=kwargs.get('temperature', 0.8)
            )

            logger.info(f"Successfully generated cooking suggestions for user {user_id}")
            return suggestions_data

        except Exception as e:
            logger.error(f"Cooking suggestions failed for user {user_id}: {str(e)}")
            raise OpenAIServiceError(f"Cooking suggestions failed: {str(e)}")

    async def _create_json_completion(
            self,
            system_content: str,
            user_content: str,
            max_tokens: int = 1500,
            temperature: float = 0.7
    ) -> dict[str, Any]:
        """Create a JSON completion using OpenAI API.

        Args:
            system_content: System message content.
            user_content: User message content.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            Parsed JSON response.

        Raises:
            OpenAIServiceError: If API call fails.
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
                temperature=temperature,
                response_format={"type": "json_object"}  # Ensures JSON response
            )

            content = response.choices[0].message.content
            if not content:
                raise OpenAIServiceError("Empty response from OpenAI")

            # Parse JSON response
            import json
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise OpenAIServiceError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise OpenAIServiceError(f"OpenAI API call failed: {str(e)}")