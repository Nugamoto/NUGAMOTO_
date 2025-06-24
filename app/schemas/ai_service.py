"""Pydantic schemas for AI services."""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import DifficultyLevel


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


class RecipeIngredient(BaseModel):
    """Schema for recipe ingredients."""

    name: Annotated[str, Field(
        min_length=1,
        max_length=100,
        description="Ingredient name"
    )]
    amount: Annotated[str, Field(
        min_length=1,
        max_length=50,
        description="Amount needed (e.g., '2 cups', '1 tbsp')"
    )]
    notes: Annotated[str | None, Field(
        None,
        max_length=200,
        description="Additional notes about the ingredient"
    )]

    model_config = ConfigDict(str_strip_whitespace=True)


class RecipeInstruction(BaseModel):
    """Schema for recipe instructions."""

    step_number: Annotated[int, Field(
        ge=1,
        description="Step number in the cooking process"
    )]
    instruction: Annotated[str, Field(
        min_length=1,
        max_length=1000,
        description="Detailed instruction for this step"
    )]
    estimated_time: Annotated[int | None, Field(
        None,
        ge=1,
        description="Estimated time for this step in minutes"
    )]

    model_config = ConfigDict(str_strip_whitespace=True)


class NutritionalInfo(BaseModel):
    """Schema for nutritional information."""

    calories_per_serving: Annotated[int | None, Field(
        None,
        ge=0,
        description="Calories per serving"
    )]
    protein_grams: Annotated[float | None, Field(
        None,
        ge=0,
        description="Protein content in grams"
    )]
    carbs_grams: Annotated[float | None, Field(
        None,
        ge=0,
        description="Carbohydrate content in grams"
    )]
    fat_grams: Annotated[float | None, Field(
        None,
        ge=0,
        description="Fat content in grams"
    )]
    fiber_grams: Annotated[float | None, Field(
        None,
        ge=0,
        description="Fiber content in grams"
    )]

    model_config = ConfigDict(from_attributes=True)


class RecipeGenerationResponse(BaseModel):
    """Response schema for recipe generation."""

    title: Annotated[str, Field(
        min_length=1,
        max_length=200,
        description="Recipe title"
    )]
    description: Annotated[str | None, Field(
        None,
        max_length=500,
        description="Brief description of the recipe"
    )]
    cuisine_type: Annotated[str | None, Field(
        None,
        max_length=50,
        description="Cuisine type"
    )]
    difficulty_level: DifficultyLevel
    prep_time_minutes: Annotated[int, Field(
        ge=0,
        description="Preparation time in minutes"
    )]
    cook_time_minutes: Annotated[int, Field(
        ge=0,
        description="Cooking time in minutes"
    )]
    total_time_minutes: Annotated[int, Field(
        ge=0,
        description="Total time in minutes"
    )]
    servings: Annotated[int, Field(
        ge=1,
        description="Number of servings"
    )]
    ingredients: Annotated[list[RecipeIngredient], Field(
        min_length=1,
        description="List of ingredients"
    )]
    instructions: Annotated[list[RecipeInstruction], Field(
        min_length=1,
        description="Cooking instructions"
    )]
    nutritional_info: NutritionalInfo | None = None
    tips: Annotated[list[str], Field(
        default_factory=list,
        description="Cooking tips and suggestions"
    )]
    tags: Annotated[list[str], Field(
        default_factory=list,
        description="Recipe tags (e.g., 'vegetarian', 'quick', 'healthy')"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True
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