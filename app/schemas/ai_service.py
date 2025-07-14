"""Pydantic schemas for AI services."""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.enums import DifficultyLevel
from app.schemas.ai_model_output import AIModelOutputRead
from app.schemas.recipe import RecipeWithDetails, RecipeCreate


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
            exclude_ingredients=[]
        )


class RecipeIngredient(BaseModel):
    """Schema for recipe ingredients with database ID."""

    id: Annotated[int, Field(
        description="Food item ID from database"
    )]
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

    def to_recipe_create(self, db: Session) -> RecipeCreate:
        """Convert AI response to RecipeCreate schema.
        
        Args:
            db: Database session for food item lookups.
        
        Returns:
            RecipeCreate instance.
        
        Raises:
            ValueError: If ingredients cannot be mapped to food items.
        """
        from app.crud.food import get_food_item_by_id, get_food_item_by_name
        from app.schemas.recipe import (
            RecipeCreate,
            RecipeIngredientCreate,
            RecipeStepCreate,
            RecipeNutritionCreate
        )

        # Map ingredients with ID-first approach
        ingredients = []
        unknown_ingredients = []

        for ing in self.ingredients:

        # Try to find by ID first (preferred method since we now require IDs)
            try:
                food_item = get_food_item_by_id(db, ing.id)
            except Exception:
                food_item = None
        
        # Fallback to name lookup if ID not found (backup safety)
            if not food_item:
                food_item = get_food_item_by_name(db, ing.name)
        
            if food_item:
            # Parse amount - extract numeric value
                try:
                    amount_parts = ing.amount.split()
                    numeric_amount = float(amount_parts[0]) if amount_parts and amount_parts[0].replace('.', '').replace(',', '').isdigit() else 1.0
                except (ValueError, IndexError):
                    numeric_amount = 1.0
            
                ingredients.append(
                    RecipeIngredientCreate(
                        food_item_id=food_item.id,
                        amount_in_base_unit=numeric_amount,  # Will need proper unit conversion
                        original_amount=numeric_amount,
                        original_unit_id=None  # Would need unit mapping logic
                    )
                )
            else:
                unknown_ingredients.append(f"{ing.name} (ID: {ing.id})")

        if unknown_ingredients:
            raise ValueError(
                f"Could not find these ingredients in database: {', '.join(unknown_ingredients)}"
            )

        # Map steps
        steps = [
            RecipeStepCreate(
                step_number=step.step_number,
                instruction=step.instruction
            )
            for step in self.instructions
        ]

        # Map nutrition if available
        nutrition = None
        if self.nutritional_info:
            nutrition = RecipeNutritionCreate(
                kcal=self.nutritional_info.calories_per_serving,
                protein_g=self.nutritional_info.protein_grams,
                fat_g=self.nutritional_info.fat_grams,
                carbs_g=self.nutritional_info.carbs_grams,
                fiber_g=self.nutritional_info.fiber_grams,
                source="ai_generated"
            )

        # Create recipe
        return RecipeCreate(
            title=self.title,
            difficulty=self.difficulty_level,
            servings=self.servings,
            tags=self.tags,
            ingredients=ingredients,
            steps=steps,
            nutrition=nutrition,
            is_ai_generated=True
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