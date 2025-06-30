"""OpenAI service implementation for NUGAMOTO AI features."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI
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
            request: RecipeGenerationRequest,
            user_id: int,
            kitchen_id: int,
            **kwargs: Any
    ) -> RecipeGenerationResponse:
        """Generate a recipe using OpenAI.

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
        try:
            # Build dynamic prompts (no await needed)
            system_prompt, user_prompt = self.prompt_builder.build_recipe_prompt(
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
            **kwargs: Additional parameters.

        Returns:
            Analysis and recommendations.

        Raises:
            OpenAIServiceError: If analysis fails.
        """
        try:
            # Build dynamic prompts (no await needed)
            system_prompt, user_prompt = self.prompt_builder.build_inventory_analysis_prompt(
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
        try:
            # Create a basic recipe request for suggestions
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

            # Generate suggestions using OpenAI
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

            # Define the function schema based on RecipeGenerationResponse with required ID
            function_schema = {
                "name": "generate_recipe",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "minLength": 1, "maxLength": 200},
                        "description": {"type": "string", "maxLength": 500},
                        "cuisine_type": {"type": "string", "maxLength": 50},
                        "difficulty_level": {"type": "string", "enum": ["easy", "medium", "hard"]},
                        "prep_time_minutes": {"type": "integer", "minimum": 0},
                        "cook_time_minutes": {"type": "integer", "minimum": 0},
                        "total_time_minutes": {"type": "integer", "minimum": 0},
                        "servings": {"type": "integer", "minimum": 1},
                        "ingredients": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer", 
                                        "description": "Required food item ID from database - must match an ID from the available ingredients list"
                                    },
                                    "name": {"type": "string", "minLength": 1, "maxLength": 100},
                                    "amount": {"type": "string", "minLength": 1, "maxLength": 50},
                                    "notes": {"type": "string", "maxLength": 200}
                                },
                                "required": ["id", "name", "amount"]
                            },
                            "minItems": 1
                        },
                        "instructions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step_number": {"type": "integer", "minimum": 1},
                                    "instruction": {"type": "string", "minLength": 1, "maxLength": 1000},
                                    "estimated_time": {"type": "integer", "minimum": 1}
                                },
                                "required": ["step_number", "instruction"]
                            },
                            "minItems": 1
                        },
                        "nutritional_info": {
                            "type": "object",
                            "properties": {
                                "calories_per_serving": {"type": "integer", "minimum": 0},
                                "protein_grams": {"type": "number", "minimum": 0},
                                "carbs_grams": {"type": "number", "minimum": 0},
                                "fat_grams": {"type": "number", "minimum": 0},
                                "fiber_grams": {"type": "number", "minimum": 0}
                            }
                        },
                        "tips": {"type": "array", "items": {"type": "string"}},
                        "tags": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": [
                        "title", "difficulty_level", "prep_time_minutes",
                        "cook_time_minutes", "total_time_minutes", "servings",
                        "ingredients", "instructions"
                    ]
                }
            }

            # Log the request details
            logger.info("Making OpenAI API request...")
            logger.debug(f"Model: {self.model}")
            logger.debug(f"Temperature: {temperature}")
            logger.debug(f"Max tokens: {max_tokens}")

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                functions=[function_schema],
                function_call={"name": "generate_recipe"}
            )

            # Log the raw response
            logger.info("Received OpenAI API response")
            logger.debug(f"Response ID: {completion.id}")
            logger.debug(f"Model used: {completion.model}")
            logger.debug(f"Usage: {completion.usage}")

            # Extract the function call result
            function_call = completion.choices[0].message.function_call
            if not function_call or not function_call.arguments:
                raise OpenAIServiceError("No function call in response")

            # Parse and log the structured output
            response_data = json.loads(function_call.arguments)
            logger.info("Successfully parsed structured output from OpenAI")
            
            # Log the structured output for debugging
            logger.debug(f"Structured output: {json.dumps(response_data, indent=2)}")

            return response_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise OpenAIServiceError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise OpenAIServiceError(f"OpenAI API call failed: {str(e)}")