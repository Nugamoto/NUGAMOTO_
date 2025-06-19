"""Pydantic schemas for recipe system v2.0."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict


# ================================================================== #
# Recipe Ingredient Schemas (v2.0)                                  #
# ================================================================== #

class _RecipeIngredientBase(BaseModel):
    """Fields shared by all recipe ingredient schemas."""

    food_item_id: int = Field(..., gt=0, description="Reference to food item")
    amount_in_base_unit: float = Field(
        ..., gt=0,
        description="Amount in the food item's base unit (e.g., grams)"
    )
    original_unit_id: int | None = Field(
        default=None, gt=0,
        description="Unit as originally entered by user"
    )
    original_amount: float | None = Field(
        default=None, gt=0,
        description="Amount as originally entered by user"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("original_amount")
    def validate_original_amount_with_unit(cls, v: float | None, info) -> float | None:
        """Validate that original_amount is provided if original_unit_id is set.
        
        Args:
            v: The original amount value.
            info: Validation context with access to other fields.
            
        Returns:
            The validated original amount.
            
        Raises:
            ValueError: If original_unit_id is set but original_amount is not.
        """
        values = info.data if hasattr(info, 'data') else {}
        original_unit_id = values.get('original_unit_id')

        if original_unit_id is not None and v is None:
            raise ValueError("original_amount is required when original_unit_id is provided")

        return v


class RecipeIngredientCreate(_RecipeIngredientBase):
    """Schema for creating a recipe ingredient."""
    pass


class RecipeIngredientRead(_RecipeIngredientBase):
    """Schema returned to the client."""

    recipe_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime | None

    # Optional nested details for display
    food_item_name: str | None = Field(
        default=None,
        description="Name of the associated food item"
    )
    base_unit_name: str | None = Field(
        default=None,
        description="Name of the food item's base unit"
    )
    original_unit_name: str | None = Field(
        default=None,
        description="Name of the original unit if available"
    )
    display_amount: float | None = Field(
        default=None,
        description="Amount to display (original or base)"
    )
    display_unit: str | None = Field(
        default=None,
        description="Unit to display (original or base)"
    )


class RecipeIngredientUpdate(BaseModel):
    """Schema for updating recipe ingredient."""

    amount_in_base_unit: float | None = Field(default=None, gt=0)
    original_unit_id: int | None = Field(default=None, gt=0)
    original_amount: float | None = Field(default=None, gt=0)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("original_amount")
    def validate_original_amount_with_unit(cls, v: float | None, info) -> float | None:
        """Validate that original_amount is provided if original_unit_id is set."""
        values = info.data if hasattr(info, 'data') else {}
        original_unit_id = values.get('original_unit_id')

        if original_unit_id is not None and v is None:
            raise ValueError("original_amount is required when original_unit_id is provided")

        return v


# ================================================================== #
# Recipe Step Schemas                                                #
# ================================================================== #

class _RecipeStepBase(BaseModel):
    """Fields shared by all recipe step schemas."""

    step_number: int = Field(..., gt=0, description="Step order in the recipe")
    instruction: str = Field(..., min_length=10, max_length=2000)

    model_config = ConfigDict(from_attributes=True)


class RecipeStepCreate(_RecipeStepBase):
    """Schema for creating a recipe step."""

    @field_validator("instruction")
    def validate_instruction(cls, v: str) -> str:
        """Validate and clean instruction text.
        
        Args:
            v: The instruction text to validate.
            
        Returns:
            The cleaned instruction text.
        """
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Instruction cannot be empty")

        # Ensure it ends with proper punctuation
        if not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'

        return cleaned


class RecipeStepRead(_RecipeStepBase):
    """Schema returned to the client."""

    id: int
    recipe_id: int
    created_at: datetime.datetime


class RecipeStepUpdate(BaseModel):
    """Schema for updating recipe step."""

    step_number: int | None = Field(default=None, gt=0)
    instruction: str | None = Field(default=None, min_length=10, max_length=2000)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("instruction")
    def validate_instruction(cls, v: str | None) -> str | None:
        """Validate and clean instruction text."""
        if v is None:
            return v

        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Instruction cannot be empty")

        # Ensure it ends with proper punctuation
        if not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'

        return cleaned


# ================================================================== #
# Recipe Nutrition Schemas                                           #
# ================================================================== #

class _RecipeNutritionBase(BaseModel):
    """Fields shared by all recipe nutrition schemas."""

    kcal: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    source: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("source")
    def validate_source(cls, v: str | None) -> str | None:
        """Validate nutrition data source.
        
        Args:
            v: The source value to validate.
            
        Returns:
            The normalized source or None.
        """
        if v is None:
            return v

        cleaned = v.strip().upper()
        valid_sources = {
            "MANUAL", "CALCULATED", "USDA", "AI_ESTIMATED",
            "NUTRITION_LABEL", "DATABASE"
        }

        if cleaned not in valid_sources:
            raise ValueError(
                f"Source must be one of: {', '.join(valid_sources)}"
            )

        return cleaned


class RecipeNutritionCreate(_RecipeNutritionBase):
    """Schema for creating recipe nutrition."""
    pass


class RecipeNutritionRead(_RecipeNutritionBase):
    """Schema returned to the client."""

    recipe_id: int
    created_at: datetime.datetime
    has_complete_macros: bool = Field(
        description="True if protein, fat, and carbs are all available"
    )
    calculated_kcal: float | None = Field(
        description="Calories calculated from macronutrients"
    )


class RecipeNutritionUpdate(BaseModel):
    """Schema for updating recipe nutrition."""

    kcal: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    source: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("source")
    def validate_source(cls, v: str | None) -> str | None:
        """Validate nutrition data source."""
        if v is None:
            return v

        cleaned = v.strip().upper()
        valid_sources = {
            "MANUAL", "CALCULATED", "USDA", "AI_ESTIMATED",
            "NUTRITION_LABEL", "DATABASE"
        }

        if cleaned not in valid_sources:
            raise ValueError(
                f"Source must be one of: {', '.join(valid_sources)}"
            )

        return cleaned


# ================================================================== #
# Recipe Schemas                                                     #
# ================================================================== #

class _RecipeBase(BaseModel):
    """Fields shared by all recipe schemas."""

    title: str = Field(..., min_length=1, max_length=255)
    is_ai_generated: bool = Field(default=False)
    created_by_user_id: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("title")
    def validate_title(cls, v: str) -> str:
        """Validate and normalize recipe title.
        
        Args:
            v: The title to validate.
            
        Returns:
            The normalized title.
        """
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty")

        # Capitalize first letter
        return cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()


class RecipeCreate(_RecipeBase):
    """Schema used on **create** (request body)."""

    ingredients: list[RecipeIngredientCreate] = Field(..., min_length=1)
    steps: list[RecipeStepCreate] = Field(..., min_length=1)
    nutrition: RecipeNutritionCreate | None = Field(default=None)

    @field_validator("steps")
    def validate_steps_sequence(cls, v: list[RecipeStepCreate]) -> list[RecipeStepCreate]:
        """Validate that step numbers form a continuous sequence starting from 1.

        Args:
            v: The list of steps to validate.

        Returns:
            The validated steps list.

        Raises:
            ValueError: If step numbers are not continuous or don't start from 1.
        """
        step_numbers = [step.step_number for step in v]
        step_numbers.sort()

        expected_sequence = list(range(1, len(v) + 1))
        if step_numbers != expected_sequence:
            raise ValueError(
                f"Step numbers must form a continuous sequence starting from 1. "
                f"Expected: {expected_sequence}, Got: {step_numbers}"
            )

        return v

    @field_validator("ingredients")
    def validate_unique_ingredients(cls, v: list[RecipeIngredientCreate]) -> list[RecipeIngredientCreate]:
        """Validate that all ingredients are unique by food_item_id.

        Args:
            v: The list of ingredients to validate.

        Returns:
            The validated ingredients list.

        Raises:
            ValueError: If duplicate food items are found.
        """
        food_item_ids = [ingredient.food_item_id for ingredient in v]
        if len(food_item_ids) != len(set(food_item_ids)):
            raise ValueError("Duplicate food items are not allowed in a recipe")

        return v


class RecipeRead(_RecipeBase):
    """Schema returned to the client."""

    id: int
    created_at: datetime.datetime
    created_by_user: dict | None = None


class RecipeWithDetails(RecipeRead):
    """Recipe with all related data for detailed view."""

    ingredients: list[RecipeIngredientRead] = Field(default_factory=list)
    steps: list[RecipeStepRead] = Field(default_factory=list)
    nutrition: RecipeNutritionRead | None = None


class RecipeUpdate(BaseModel):
    """Schema for updating recipe."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_ai_generated: bool | None = Field(default=None)
    created_by_user_id: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("title")
    def validate_title(cls, v: str | None) -> str | None:
        """Validate and normalize recipe title."""
        if v is None:
            return v

        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty")

        # Capitalize first letter
        return cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()


# ================================================================== #
# Search and Filter Parameters                                       #
# ================================================================== #

class RecipeSearchParams(BaseModel):
    """Parameters for filtering recipes."""

    title_contains: str | None = Field(default=None, min_length=1)
    is_ai_generated: bool | None = None
    created_by_user_id: int | None = Field(default=None, gt=0)
    has_nutrition: bool | None = None
    max_kcal: float | None = Field(default=None, gt=0)
    min_protein_g: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(from_attributes=True)


class RecipeSummary(BaseModel):
    """Summary statistics for recipes."""

    total_recipes: int = Field(ge=0)
    ai_generated_count: int = Field(ge=0)
    manual_count: int = Field(ge=0)
    with_nutrition_count: int = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Recipe Review Schemas                                              #
# ================================================================== #

class _RecipeReviewBase(BaseModel):
    """Fields shared by all recipe review schemas."""

    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("rating")
    def validate_rating(cls, v: int) -> int:
        """Validate rating is between 1 and 5.
        
        Args:
            v: The rating value to validate.
            
        Returns:
            The validated rating.
            
        Raises:
            ValueError: If rating is not between 1 and 5.
        """
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("comment")
    def validate_comment(cls, v: str | None) -> str | None:
        """Validate and clean comment text.
        
        Args:
            v: The comment to validate.
            
        Returns:
            The cleaned comment or None.
        """
        if v is None:
            return v

        cleaned = v.strip()
        return cleaned if cleaned else None


class RecipeReviewRead(_RecipeReviewBase):
    """Schema returned to the client."""

    user_id: int
    recipe_id: int
    created_at: datetime.datetime
    user: dict | None = None


class RecipeReviewUpdate(BaseModel):
    """Schema for updating recipe review."""

    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("rating")
    def validate_rating(cls, v: int | None) -> int | None:
        """Validate rating is between 1 and 5."""
        if v is not None and not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class RecipeReviewUpsert(_RecipeReviewBase):
    """Schema for creating or updating review (upsert operation)."""
    pass


# ================================================================== #
# Rating Summary Schemas                                             #
# ================================================================== #

class RecipeRatingSummary(BaseModel):
    """Summary of ratings for a recipe."""

    recipe_id: int
    total_reviews: int = Field(ge=0)
    average_rating: float | None = Field(ge=1.0, le=5.0)
    rating_distribution: dict[str, int] = Field(
        description="Count of each rating (1-5 stars)"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("rating_distribution")
    def validate_rating_distribution(cls, v: dict[str, int]) -> dict[str, int]:
        """Validate rating distribution has correct keys and values.
        
        Args:
            v: The rating distribution to validate.
            
        Returns:
            The validated rating distribution.
        """
        expected_keys = {"1", "2", "3", "4", "5"}
        if not expected_keys.issubset(v.keys()):
            raise ValueError("Rating distribution must include all ratings 1-5")

        for rating, count in v.items():
            if count < 0:
                raise ValueError("Rating counts cannot be negative")
        
        return v


# ================================================================== #
# Convenience Schemas                                                #
# ================================================================== #

class RecipeIngredientCreateWithConversion(BaseModel):
    """Future schema for creating ingredients with automatic unit conversion.
    
    This would allow users to input ingredients in any unit and
    automatically calculate the amount_in_base_unit.
    """

    food_item_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    unit_id: int = Field(..., gt=0)
    # amount_in_base_unit would be calculated automatically

    model_config = ConfigDict(from_attributes=True)


class RecipeScalingRequest(BaseModel):
    """Request to scale a recipe for different serving sizes."""

    recipe_id: int = Field(..., gt=0)
    original_servings: int = Field(..., gt=0)
    target_servings: int = Field(..., gt=0)

    model_config = ConfigDict(from_attributes=True)


class RecipeScalingResponse(BaseModel):
    """Response with scaled recipe ingredients."""

    recipe: RecipeRead
    scaled_ingredients: list[RecipeIngredientRead]
    scaling_factor: float = Field(gt=0)

    model_config = ConfigDict(from_attributes=True)
