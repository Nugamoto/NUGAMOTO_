
"""Pydantic schemas for AI services."""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import DifficultyLevel
from app.schemas.ai_model_output import AIModelOutputRead
from app.schemas.recipe import RecipeWithDetails, RecipeCreate, RecipeIngredientCreate, RecipeStepCreate, \
    RecipeNutritionCreate


# ================================================================== #
# Recipe Generation Schemas                                          #
# ================================================================== #

class RecipeGenerationRequest(BaseModel):
    """Request schema for recipe generation."""

    cuisine_type: Annotated[str | None, Field(
        None,
        max_length=50,
        description="Preferred cuisine type (e.g., 'Italian', 'Asian')"
    )]
    meal_type: Annotated[str | None, Field(
        None,
        max_length=30,
        description="Type of meal (e.g., 'breakfast', 'lunch', 'dinner', 'snack')"
    )]
    difficulty_level: DifficultyLevel | None = Field(
        None,
        description="Preferred difficulty level"
    )
    max_prep_time: Annotated[int | None, Field(
        None,
        ge=1,
        le=480,
        description="Maximum preparation time in minutes"
    )]
    max_cook_time: Annotated[int | None, Field(
        None,
        ge=1,
        le=480,
        description="Maximum cooking time in minutes"
    )]
    servings: Annotated[int | None, Field(
        None,
        ge=1,
        le=20,
        description="Number of servings"
    )]
    dietary_restrictions: Annotated[list[str], Field(
        default_factory=list,
        description="List of dietary restrictions"
    )]
    exclude_ingredients: Annotated[list[str], Field(
        default_factory=list,
        description="Ingredients to exclude from the recipe"
    )]
    special_requests: Annotated[str | None, Field(
        None,
        max_length=500,
        description="Any special requests or preferences"
    )]

    # New contextual fields for better AI prompting
    prioritize_expiring: bool = Field(
        default=True,
        description="Prioritize ingredients that are expiring soon"
    )
    prefer_available_ingredients: bool = Field(
        default=True,
        description="Prefer using ingredients available in kitchen inventory"
    )
    required_appliances: list[str] = Field(
        default_factory=list,
        description="List of required appliances for the recipe"
    )
    avoid_appliances: list[str] = Field(
        default_factory=list,
        description="List of appliances to avoid using"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('meal_type', 'cuisine_type')
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Validate and normalize text fields."""
        if v is None:
            return v
        if not v.strip():
            return None
        return v.strip().lower()

    @classmethod
    def from_user_input(cls, user_input: str) -> RecipeGenerationRequest:
        return cls(
            special_requests=user_input,
            cuisine_type=None,
            meal_type=None,
            difficulty_level=None,
            max_prep_time=None,
            max_cook_time=None,
            servings=None,
            dietary_restrictions=[],
            exclude_ingredients=[],
            prioritize_expiring=True,
            prefer_available_ingredients=True,
            required_appliances=[],
            avoid_appliances=[]
        )


class RecipeGenerationResponse(BaseModel):
    """AI Response Schema - uses existing recipe schemas for consistency."""

    # Basic recipe info
    title: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str | None, Field(None, max_length=500)]
    cuisine_type: Annotated[str | None, Field(None, max_length=100)]
    difficulty_level: DifficultyLevel
    prep_time_minutes: Annotated[int, Field(ge=0)]
    cook_time_minutes: Annotated[int, Field(ge=0)]
    total_time_minutes: Annotated[int, Field(ge=0)]
    servings: Annotated[int, Field(ge=1, le=20)]

    # Use existing schemas directly
    ingredients: Annotated[list[RecipeIngredientCreate], Field(min_length=1)]
    steps: Annotated[list[RecipeStepCreate], Field(min_length=1)]
    nutrition: RecipeNutritionCreate | None = None

    # Optional fields
    tips: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True
    )

    def to_recipe_create(self, created_by_user_id: int) -> RecipeCreate:
        """Convert to RecipeCreate - direct mapping since we use same schemas."""
        return RecipeCreate(
            title=self.title,
            description=self.description,
            cuisine_type=self.cuisine_type,
            prep_time_minutes=self.prep_time_minutes,
            cook_time_minutes=self.cook_time_minutes,
            total_time_minutes=self.total_time_minutes,
            difficulty=self.difficulty_level,
            servings=self.servings,
            tags=self.tags,
            ingredients=self.ingredients,  # Direct assignment!
            steps=self.steps,  # Direct assignment!
            nutrition=self.nutrition,  # Direct assignment!
            is_ai_generated=True,
            created_by_user_id=created_by_user_id
        )


# ================================================================== #
# Inventory Analysis Schemas                                         #
# ================================================================== #

class InventoryAnalysisRequest(BaseModel):
    """Request schema for inventory analysis."""

    kitchen_id: Annotated[int, Field(
        gt=0,
        description="Kitchen ID to analyze"
    )]
    analysis_type: Annotated[str, Field(
        default="comprehensive",
        description="Type of analysis to perform"
    )]

    model_config = ConfigDict(from_attributes=True)


class InventoryInsight(BaseModel):
    """Schema for inventory insights."""

    category: Annotated[str, Field(
        min_length=1,
        max_length=50,
        description="Insight category"
    )]
    message: Annotated[str, Field(
        min_length=1,
        max_length=500,
        description="Insight message"
    )]
    priority: Annotated[str, Field(
        default="medium",
        description="Priority level (low, medium, high)"
    )]
    items_affected: Annotated[list[str], Field(
        default_factory=list,
        description="List of affected items"
    )]

    model_config = ConfigDict(str_strip_whitespace=True)


class InventoryAnalysisResponse(BaseModel):
    """Response schema for inventory analysis."""

    kitchen_id: int
    analysis_date: datetime.datetime
    insights: list[InventoryInsight]
    recommendations: list[str] = Field(
        default_factory=list,
        description="General recommendations"
    )
    suggested_recipes: list[str] = Field(
        default_factory=list,
        description="Suggested recipes to use expiring ingredients"
    )

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# General AI Schemas                                                 #
# ================================================================== #

class AIServiceRequest(BaseModel):
    """Base schema for AI service requests."""

    user_id: Annotated[int, Field(
        gt=0,
        description="ID of the requesting user"
    )]
    kitchen_id: Annotated[int, Field(
        gt=0,
        description="ID of the target kitchen"
    )]
    context: Annotated[dict[str, Any], Field(
        default_factory=dict,
        description="Additional context for the AI request"
    )]

    model_config = ConfigDict(from_attributes=True)


class AIServiceResponse(BaseModel):
    """Base schema for AI service responses."""

    success: bool = Field(description="Whether the request was successful")
    message: str | None = Field(None, description="Response message")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Response data"
    )
    generated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc),
        description="Timestamp when response was generated"
    )

    model_config = ConfigDict(from_attributes=True)


class RecipeRequestInput(BaseModel):
    """Schema for recipe generation user input."""

    user_input: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's recipe request in natural language"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    def to_generation_request(self) -> RecipeGenerationRequest:
        """Convert user input to structured generation request using factory method."""
        return RecipeGenerationRequest.from_user_input(self.user_input)


class RecipeWithAIOutput(BaseModel):
    """Schema combining recipe and its AI generation metadata."""

    recipe: RecipeWithDetails
    ai_output: AIModelOutputRead

    model_config = ConfigDict(from_attributes=True)