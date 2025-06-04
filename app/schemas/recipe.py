"""Pydantic schemas for recipe input / output."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

from app.schemas.inventory import FoodItemRead
from app.schemas.user import UserRead


# ------------------------------------------------------------------ #
# RecipeIngredient Schemas                                           #
# ------------------------------------------------------------------ #

class _RecipeIngredientBase(BaseModel):
    """Fields shared by all recipe ingredient-related schemas."""

    food_item_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0.0)
    unit: str = Field(..., min_length=1, max_length=20)

    model_config = ConfigDict(from_attributes=True)


class RecipeIngredientCreate(_RecipeIngredientBase):
    """Schema used on **create** (request body)."""
    pass


class RecipeIngredientRead(_RecipeIngredientBase):
    """Schema returned to the client."""

    recipe_id: int
    food_item: FoodItemRead


class RecipeIngredientUpdate(_RecipeIngredientBase):
    """Schema for partial recipe ingredient updates."""

    food_item_id: int | None = Field(default=None, gt=0)
    amount: float | None = Field(default=None, gt=0.0)
    unit: str | None = Field(default=None, min_length=1, max_length=20)


# ------------------------------------------------------------------ #
# RecipeStep Schemas                                                 #
# ------------------------------------------------------------------ #

class _RecipeStepBase(BaseModel):
    """Fields shared by all recipe step-related schemas."""

    step_number: int = Field(..., gt=0)
    instruction: str = Field(..., min_length=1)

    model_config = ConfigDict(from_attributes=True)


class RecipeStepCreate(_RecipeStepBase):
    """Schema used on **create** (request body)."""

    @field_validator("instruction")
    def validate_instruction(cls, v: str) -> str:
        """Normalize instruction text.

        Args:
            v: The instruction text to validate.

        Returns:
            The normalized instruction text.
        """
        return v.strip()


class RecipeStepRead(_RecipeStepBase):
    """Schema returned to the client."""

    id: int
    recipe_id: int


class RecipeStepUpdate(_RecipeStepBase):
    """Schema for partial recipe step updates."""

    step_number: int | None = Field(default=None, gt=0)
    instruction: str | None = Field(default=None, min_length=1)

    @field_validator("instruction")
    def validate_instruction(cls, v: str | None) -> str | None:
        """Normalize instruction text.

        Args:
            v: The instruction text to validate.

        Returns:
            The normalized instruction text or None.
        """
        if v is None:
            return v
        return v.strip()


# ------------------------------------------------------------------ #
# RecipeNutrition Schemas                                            #
# ------------------------------------------------------------------ #

class _RecipeNutritionBase(BaseModel):
    """Fields shared by all recipe nutrition-related schemas."""

    kcal: float | None = Field(default=None, ge=0.0)
    protein_g: float | None = Field(default=None, ge=0.0)
    fat_g: float | None = Field(default=None, ge=0.0)
    carbs_g: float | None = Field(default=None, ge=0.0)
    fiber_g: float | None = Field(default=None, ge=0.0)
    source: str = Field(default="calculated", max_length=50)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("source")
    def validate_source(cls, v: str) -> str:
        """Validate nutrition source.

        Args:
            v: The source value to validate.

        Returns:
            The validated source.

        Raises:
            ValueError: If the source is not valid.
        """
        valid_sources = {"calculated", "user", "openfoodfacts", "usda"}
        if v not in valid_sources:
            raise ValueError(
                f"Source must be one of: {', '.join(valid_sources)}. Got: {v}"
            )
        return v


class RecipeNutritionCreate(_RecipeNutritionBase):
    """Schema used on **create** (request body)."""
    pass


class RecipeNutritionRead(_RecipeNutritionBase):
    """Schema returned to the client."""

    recipe_id: int
    has_complete_macros: bool = Field(..., description="True if protein, fat, and carbs are all present")
    calculated_kcal: float | None = Field(..., description="Calories calculated from macros")


class RecipeNutritionUpdate(_RecipeNutritionBase):
    """Schema for partial recipe nutrition updates."""

    kcal: float | None = Field(default=None, ge=0.0)
    protein_g: float | None = Field(default=None, ge=0.0)
    fat_g: float | None = Field(default=None, ge=0.0)
    carbs_g: float | None = Field(default=None, ge=0.0)
    fiber_g: float | None = Field(default=None, ge=0.0)
    source: str | None = Field(default=None, max_length=50)

    @field_validator("source")
    def validate_source(cls, v: str | None) -> str | None:
        """Validate nutrition source.

        Args:
            v: The source value to validate.

        Returns:
            The validated source or None.

        Raises:
            ValueError: If the source is not valid.
        """
        if v is None:
            return v
        valid_sources = {"calculated", "user", "openfoodfacts", "usda"}
        if v not in valid_sources:
            raise ValueError(
                f"Source must be one of: {', '.join(valid_sources)}. Got: {v}"
            )
        return v


# ------------------------------------------------------------------ #
# Recipe Schemas                                                     #
# ------------------------------------------------------------------ #

class _RecipeBase(BaseModel):
    """Fields shared by all recipe-related schemas."""

    title: str = Field(..., min_length=1, max_length=255)
    is_ai_generated: bool = Field(default=False)
    created_by_user_id: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("title")
    def validate_title(cls, v: str) -> str:
        """Normalize recipe title.

        Args:
            v: The title to validate.

        Returns:
            The normalized title.
        """
        return v.strip().title()


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
    created_by_user: UserRead | None = Field(default=None)


class RecipeWithDetails(RecipeRead):
    """Recipe schema that includes all related data."""

    ingredients: list[RecipeIngredientRead] = Field(default_factory=list)
    steps: list[RecipeStepRead] = Field(default_factory=list)
    nutrition: RecipeNutritionRead | None = Field(default=None)


class RecipeUpdate(_RecipeBase):
    """Schema for partial recipe updates (PATCH operations)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_ai_generated: bool | None = Field(default=None)
    created_by_user_id: int | None = Field(default=None, gt=0)

    @field_validator("title")
    def validate_title(cls, v: str | None) -> str | None:
        """Normalize recipe title.

        Args:
            v: The title to validate.

        Returns:
            The normalized title or None.
        """
        if v is None:
            return v
        return v.strip().title()


# ------------------------------------------------------------------ #
# Search and Filter Schemas                                          #
# ------------------------------------------------------------------ #

class RecipeSearchParams(BaseModel):
    """Parameters for recipe search and filtering."""

    title_contains: str | None = Field(default=None, min_length=1)
    is_ai_generated: bool | None = Field(default=None)
    created_by_user_id: int | None = Field(default=None, gt=0)
    has_nutrition: bool | None = Field(default=None)
    max_kcal: float | None = Field(default=None, gt=0)
    min_protein_g: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(from_attributes=True)


class RecipeSummary(BaseModel):
    """Summary statistics for recipes."""

    total_recipes: int = Field(..., description="Total number of recipes")
    ai_generated_count: int = Field(..., description="Number of AI-generated recipes")
    manual_count: int = Field(..., description="Number of manually created recipes")
    with_nutrition_count: int = Field(..., description="Number of recipes with nutrition data")

    model_config = ConfigDict(from_attributes=True)
