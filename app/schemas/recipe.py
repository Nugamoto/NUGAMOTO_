
"""Pydantic schemas for recipe input / output."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

from app.core.enums import DifficultyLevel
from app.schemas.user import UserRead


# ================================================================== #
# Recipe Ingredient Schemas                                          #
# ================================================================== #

class _RecipeIngredientBase(BaseModel):
    """Fields shared by all recipe ingredient schemas."""

    food_item_id: int = Field(..., gt=0)
    amount_in_base_unit: float = Field(..., gt=0)
    original_unit_id: int | None = Field(default=None, gt=0)
    original_amount: float | None = Field(default=None, gt=0)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('original_amount')
    def validate_original_amount_with_unit(cls, v, info):
        """Ensure original_amount and original_unit_id are both provided or both None."""
        values = info.data
        original_unit_id = values.get('original_unit_id')

        if v is not None and original_unit_id is None:
            raise ValueError("original_unit_id is required when original_amount is provided")
        if v is None and original_unit_id is not None:
            raise ValueError("original_amount is required when original_unit_id is provided")

        return v


class RecipeIngredientCreate(_RecipeIngredientBase):
    """Schema used on **create** (request body)."""
    pass


class RecipeIngredientRead(_RecipeIngredientBase):
    """Schema returned to the client."""

    recipe_id: int
    created_at: datetime
    updated_at: datetime

    # Computed fields populated by CRUD builders
    food_item_name: str = Field(..., description="Name of the food item")
    base_unit_name: str = Field(..., description="Base unit of the food item")
    original_unit_name: str | None = Field(None, description="Original unit name if available")
    display_amount: float = Field(..., description="Amount to display")
    display_unit: str = Field(..., description="Unit to display")


class RecipeIngredientUpdate(_RecipeIngredientBase):
    """Schema for partial ingredient updates (PATCH operations)."""

    food_item_id: int | None = Field(default=None, gt=0)
    amount_in_base_unit: float | None = Field(default=None, gt=0)
    original_unit_id: int | None = Field(default=None, gt=0)
    original_amount: float | None = Field(default=None, gt=0)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('original_amount')
    def validate_original_amount_with_unit(cls, v, info):
        """Ensure original_amount and original_unit_id are both provided or both None."""
        values = info.data
        original_unit_id = values.get('original_unit_id')

        if v is not None and original_unit_id is None:
            raise ValueError("original_unit_id is required when original_amount is provided")
        if v is None and original_unit_id is not None:
            raise ValueError("original_amount is required when original_unit_id is provided")

        return v


# ================================================================== #
# Recipe Step Schemas                                                #
# ================================================================== #

class _RecipeStepBase(BaseModel):
    """Fields shared by all recipe step schemas."""

    step_number: int = Field(..., ge=1)
    instruction: str = Field(..., min_length=1)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )


class RecipeStepCreate(_RecipeStepBase):
    """Schema used on **create** (request body)."""

    @field_validator('instruction')
    def validate_instruction(cls, v: str) -> str:
        """Validate and normalize instruction."""
        if not v or v.isspace():
            raise ValueError("Instruction cannot be empty or whitespace")
        return v.strip()


class RecipeStepRead(_RecipeStepBase):
    """Schema returned to the client."""

    id: int
    recipe_id: int
    created_at: datetime
    updated_at: datetime



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
    source: str = Field(default="manual", max_length=50)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('source')
    def validate_source(cls, v: str) -> str:
        """Validate and normalize source."""
        allowed_sources = {"manual", "calculated", "api", "imported", "ai_generated"}
        v_lower = v.lower().strip()
        if v_lower not in allowed_sources:
            raise ValueError(f"Source must be one of: {', '.join(allowed_sources)}")
        return v_lower


class RecipeNutritionCreate(_RecipeNutritionBase):
    """Schema used on **create** (request body)."""
    pass


class RecipeNutritionRead(_RecipeNutritionBase):
    """Schema returned to the client."""

    recipe_id: int
    created_at: datetime
    updated_at: datetime

    # Computed fields populated by CRUD builders
    has_complete_macros: bool = Field(..., description="Whether all macros are available")
    calculated_kcal: float | None = Field(None, description="Calculated calories from macros")


class RecipeNutritionUpdate(_RecipeNutritionBase):
    """Schema for partial nutrition updates (PATCH operations)."""

    kcal: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fiber_g: float | None = Field(default=None, ge=0)
    source: str | None = Field(default=None, max_length=50)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('source')
    def validate_source(cls, v: str | None) -> str | None:
        """Validate and normalize source."""
        if v is None:
            return v
        allowed_sources = {"manual", "calculated", "api", "imported", "ai_generated"}
        v_lower = v.lower().strip()
        if v_lower not in allowed_sources:
            raise ValueError(f"Source must be one of: {', '.join(allowed_sources)}")
        return v_lower


# ================================================================== #
# Recipe Base and Main Schemas                                       #
# ================================================================== #

class _RecipeBase(BaseModel):
    """Fields shared by all recipe-related schemas."""

    title: str = Field(..., min_length=1, max_length=255)
    is_ai_generated: bool = Field(default=False)
    created_by_user_id: int | None = Field(default=None, gt=0)
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM)
    servings: int = Field(default=1, ge=1, le=20)
    tags: list[str] | None = Field(default=None)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('title')
    def validate_title(cls, v: str) -> str:
        """Validate and normalize title."""
        if not v or v.isspace():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator('tags')
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate and normalize tags."""
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("Tags must be a list")

        cleaned_tags = []
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            cleaned_tag = tag.strip()
            if cleaned_tag and cleaned_tag not in cleaned_tags:
                cleaned_tags.append(cleaned_tag)

        return cleaned_tags if cleaned_tags else None


class RecipeCreate(_RecipeBase):
    """Schema for creating recipes with related entities."""

    ingredients: list[RecipeIngredientCreate] = Field(..., min_length=1)
    steps: list[RecipeStepCreate] = Field(..., min_length=1)
    nutrition: RecipeNutritionCreate | None = None

    @field_validator("steps")
    def validate_steps_sequence(cls, v):
        """Validate that steps have sequential numbering."""
        if not v:
            raise ValueError("At least one step is required")

        step_numbers = [step.step_number for step in v]
        step_numbers.sort()

        expected_numbers = list(range(1, len(step_numbers) + 1))
        if step_numbers != expected_numbers:
            raise ValueError("Steps must be numbered sequentially starting from 1")

        return v

    @field_validator("ingredients")
    def validate_unique_ingredients(cls, v):
        """Validate that ingredients don't have duplicate food items."""
        if not v:
            raise ValueError("At least one ingredient is required")

        food_item_ids = [ingredient.food_item_id for ingredient in v]
        if len(food_item_ids) != len(set(food_item_ids)):
            raise ValueError("Duplicate food items are not allowed in ingredients")

        return v


class RecipeRead(_RecipeBase):
    """Schema returned to the client."""

    id: int
    created_at: datetime
    updated_at: datetime
    created_by_user: UserRead | None = None


class RecipeWithDetails(_RecipeBase):
    """Schema returned with full recipe details."""

    id: int
    created_at: datetime
    updated_at: datetime
    created_by_user: UserRead | None = None

    ingredients: list[RecipeIngredientRead] = Field(default_factory=list)
    steps: list[RecipeStepRead] = Field(default_factory=list)
    nutrition: RecipeNutritionRead | None = None


class RecipeUpdate(_RecipeBase):
    """Schema for partial recipe updates (PATCH operations)."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    is_ai_generated: bool | None = None
    created_by_user_id: int | None = Field(default=None, gt=0)
    difficulty: DifficultyLevel | None = None
    servings: int | None = Field(default=None, ge=1, le=20)
    tags: list[str] | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('title')
    def validate_title(cls, v: str | None) -> str | None:
        """Validate and normalize title."""
        if v is None:
            return v
        if not v or v.isspace():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator('tags')
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate and normalize tags."""
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("Tags must be a list")

        cleaned_tags = []
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
            cleaned_tag = tag.strip()
            if cleaned_tag and cleaned_tag not in cleaned_tags:
                cleaned_tags.append(cleaned_tag)

        return cleaned_tags if cleaned_tags else None


# ================================================================== #
# Search and Filter Parameters                                       #
# ================================================================== #

class RecipeSearchParams(BaseModel):
    """Parameters for searching recipes."""

    title_contains: str | None = None
    is_ai_generated: bool | None = None
    created_by_user_id: int | None = Field(default=None, gt=0)
    difficulty: DifficultyLevel | None = None
    has_nutrition: bool | None = None
    max_kcal: float | None = Field(default=None, gt=0)
    min_protein_g: float | None = Field(default=None, ge=0)
    tags_contains: list[str] | None = Field(default=None)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )


class RecipeSummary(BaseModel):
    """Summary statistics for recipes."""

    total_recipes: int = Field(..., ge=0)
    ai_generated_count: int = Field(..., ge=0)
    manual_count: int = Field(..., ge=0)
    with_nutrition_count: int = Field(..., ge=0)
    by_difficulty: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )


# ================================================================== #
# Recipe Review Schemas                                              #
# ================================================================== #

class _RecipeReviewBase(BaseModel):
    """Fields shared by all recipe review schemas."""

    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('rating')
    def validate_rating(cls, v: int) -> int:
        """Validate rating is between 1 and 5."""
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator('comment')
    def validate_comment(cls, v: str | None) -> str | None:
        """Validate and normalize comment."""
        if v is None:
            return v
        if not v or v.isspace():
            raise ValueError("Comment cannot be empty or whitespace")
        return v.strip()


class RecipeReviewRead(_RecipeReviewBase):
    """Schema returned to the client."""

    user_id: int
    recipe_id: int
    created_at: datetime
    updated_at: datetime
    user: UserRead


class RecipeReviewUpdate(_RecipeReviewBase):
    """Schema for partial review updates (PATCH operations)."""

    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('rating')
    def validate_rating(cls, v: int | None) -> int | None:
        """Validate rating is between 1 and 5."""
        if v is None:
            return v
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class RecipeReviewUpsert(_RecipeReviewBase):
    """Schema for creating or updating reviews."""
    pass


class RecipeRatingSummary(BaseModel):
    """Rating summary for a recipe."""

    recipe_id: int
    total_reviews: int = Field(..., ge=0)
    average_rating: float | None = Field(None, ge=1, le=5)
    rating_distribution: dict[str, int]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )


# ================================================================== #
# AI Integration Schemas                                             #
# ================================================================== #

class RecipeCreateFromAI(_RecipeBase):
    """Schema for creating recipes from AI with additional metadata."""

    ingredients: list[RecipeIngredientCreate] = Field(..., min_length=1)
    steps: list[RecipeStepCreate] = Field(..., min_length=1)
    nutrition: RecipeNutritionCreate | None = None

    # AI metadata
    ai_model_version: str | None = Field(default=None, max_length=100)
    ai_prompt_used: str | None = Field(default=None)
    ai_raw_output: str | None = Field(default=None)

    # Override default
    is_ai_generated: bool = Field(default=True)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )


class RecipeWithAIMetadata(RecipeWithDetails):
    """Recipe with AI generation metadata if available."""

    ai_model_version: str | None = Field(default=None)
    ai_generation_date: datetime | None = Field(default=None)
    ai_prompt_summary: str | None = Field(default=None)
