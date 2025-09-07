"""OpenAI service implementation for NUGAMOTO AI features."""

from __future__ import annotations

import json
import logging
from typing import Any, TypeVar, TYPE_CHECKING

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam
)
from openai.types.shared_params import ResponseFormatJSONObject
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.config import settings

if TYPE_CHECKING:
    from backend.schemas.ai_service import RecipeGenerationRequest, RecipeGenerationResponse
from backend.services.ai.base import AIService
from backend.services.ai.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

# Type variable for structured completion return type
T = TypeVar('T', bound=BaseModel)


class OpenAIServiceError(Exception):
    """Custom exception for OpenAI service errors."""
    pass


class OpenAIService(AIService):
    """OpenAI service implementation for AI features."""

    def __init__(
            self,
            db: Session,
            model: str = "gpt-4o-mini",
            api_key: str | None = None
    ):
        """Initialize the OpenAI service.

        Args:
            db: Database session for accessing kitchen data.
            model: OpenAI model to use.
            api_key: Optional API key override.
        """
        self.db = db
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise OpenAIServiceError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.prompt_builder = PromptBuilder(db)
        logger.debug(f"Initialized OpenAIService with model: {model}")

    async def generate_recipe(
            self,
            request: "RecipeGenerationRequest",
            user_id: int,
            kitchen_id: int,
            **kwargs: Any
    ) -> "RecipeGenerationResponse":
        """Generate a recipe using OpenAI with structured output.

        Args:
            request: Recipe generation request with preferences.
            user_id: ID of the requesting user.
            kitchen_id: ID of the kitchen.
            **kwargs: Additional parameters.

        Returns:
            Structured recipe response.

        Raises:
            OpenAIServiceError: If recipe generation fails.
        """
        from backend.schemas.ai_service import RecipeGenerationResponse

        try:
            # Build dynamic prompts
            system_prompt, user_prompt = self.prompt_builder.build_recipe_prompt(
                request=request,
                user_id=user_id,
                kitchen_id=kitchen_id
            )

            # Generate recipe using structured output with existing schemas
            recipe_response = await self._create_structured_completion(
                system_content=system_prompt,
                user_content=user_prompt,
                response_model=RecipeGenerationResponse,
                max_tokens=kwargs.get('max_tokens', 2000),
                temperature=kwargs.get('temperature', 0.7)
            )

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
            **kwargs: Additional parameters.

        Returns:
            Analysis and recommendations.

        Raises:
            OpenAIServiceError: If analysis fails.
        """
        try:
            # Build dynamic prompts
            system_prompt, user_prompt = self.prompt_builder.build_inventory_analysis_prompt(
                kitchen_id=kitchen_id
            )

            # Generate analysis using structured output
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
        """Get personalized cooking suggestions using OpenAI.

        Args:
            kitchen_id: ID of the kitchen.
            user_id: ID of the user requesting suggestions.
            **kwargs: Additional parameters.

        Returns:
            Dictionary containing personalized cooking suggestions.

        Raises:
            OpenAIServiceError: If suggestion generation fails.
        """
        from backend.schemas.ai_service import RecipeGenerationRequest

        try:
            # Create a basic recipe request for suggestions - now uses default_factory
            suggestion_request = RecipeGenerationRequest(
                special_requests="Provide 3-5 quick meal suggestions based on available ingredients"
            )

            # Use recipe generation prompt with modified prompt for suggestions
            system_prompt, user_prompt = self.prompt_builder.build_recipe_prompt(
                request=suggestion_request,
                user_id=user_id,
                kitchen_id=kitchen_id
            )

            # Modify system prompt for suggestions
            suggestion_system_prompt = system_prompt.replace(
                "Provide responses in valid JSON format with the specified schema.",
                """Provide 3-5 quick meal suggestions in JSON format with the following structure:
                {
                    "suggestions": [
                        {
                            "title": "Recipe title",
                            "description": "Brief description",
                            "estimated_time": "Total time in minutes",
                            "difficulty": "easy/medium/hard",
                            "main_ingredients": ["ingredient1", "ingredient2"]
                        }
                    ]
                }"""
            )

            # Generate suggestions using JSON completion
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

    async def _create_structured_completion(
            self,
            system_content: str,
            user_content: str,
            response_model: type[T],
            max_tokens: int = 2000,
            temperature: float = 0.7
    ) -> T:
        """Create completion with structured output using Pydantic model.

        Args:
            system_content: System prompt content.
            user_content: User prompt content.
            response_model: Pydantic model class for structured output.
            max_tokens: Maximum tokens for response.
            temperature: Temperature for response generation.

        Returns:
            Parsed and validated Pydantic model instance.

        Raises:
            OpenAIServiceError: If completion fails.
        """
        try:
            messages = [
                ChatCompletionSystemMessageParam(role="system", content=system_content),
                ChatCompletionUserMessageParam(role="user", content=user_content)
            ]

            logger.info(f"Making OpenAI API request with structured output: {response_model.__name__}")
            logger.debug(f"Model: {self.model}")
            logger.debug(f"Temperature: {temperature}")
            logger.debug(f"Max tokens: {max_tokens}")

            # Use beta.chat.completions.parse with existing recipe schemas
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
                max_tokens=max_tokens,
                temperature=temperature
            )

            logger.info("Received structured response from OpenAI")
            logger.debug(f"Response ID: {completion.id}")
            logger.debug(f"Model used: {completion.model}")
            logger.debug(f"Usage: {completion.usage}")

            # The parse method automatically validates and returns the Pydantic model
            parsed_response = completion.choices[0].message.parsed
            logger.info("Successfully parsed and validated structured output")

            return parsed_response

        except Exception as e:
            logger.error(f"Structured completion failed: {str(e)}")
            raise OpenAIServiceError(f"Structured completion failed: {str(e)}")

    async def _create_json_completion(
            self,
            system_content: str,
            user_content: str,
            max_tokens: int = 1500,
            temperature: float = 0.7
    ) -> dict[str, Any]:
        """Create JSON completion for non-recipe structured responses.

        This method is kept for backward compatibility and non-recipe AI features
        like inventory analysis and cooking suggestions.

        Args:
            system_content: System prompt content.
            user_content: User prompt content.
            max_tokens: Maximum tokens for response.
            temperature: Temperature for response generation.

        Returns:
            Dictionary containing the JSON response.

        Raises:
            OpenAIServiceError: If completion fails.
        """
        try:
            messages = [
                ChatCompletionSystemMessageParam(role="system", content=system_content),
                ChatCompletionUserMessageParam(role="user", content=user_content)
            ]

            logger.info("Making OpenAI API request with JSON response format")
            logger.debug(f"Model: {self.model}")
            logger.debug(f"Temperature: {temperature}")
            logger.debug(f"Max tokens: {max_tokens}")

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format=ResponseFormatJSONObject(type="json_object"),
                max_tokens=max_tokens,
                temperature=temperature
            )

            logger.info("Received JSON response from OpenAI")
            logger.debug(f"Response ID: {completion.id}")
            logger.debug(f"Model used: {completion.model}")
            logger.debug(f"Usage: {completion.usage}")

            # Parse JSON response
            response_content = completion.choices[0].message.content
            if not response_content:
                raise OpenAIServiceError("Empty response from OpenAI")

            response_data = json.loads(response_content)
            logger.info("Successfully parsed JSON response")

            return response_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise OpenAIServiceError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"JSON completion failed: {str(e)}")
            raise OpenAIServiceError(f"JSON completion failed: {str(e)}")