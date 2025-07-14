"""Pydantic schemas for AI services."""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.enums import DifficultyLevel
from app.schemas.ai_model_output import AIModelOutputRead
from app.schemas.device import ApplianceWithDeviceType, KitchenToolWithDeviceType
from app.schemas.inventory import InventoryItemRead
from app.schemas.recipe import RecipeWithDetails, RecipeCreate, RecipeIngredientCreate, RecipeStepCreate, \
    RecipeNutritionCreate
from app.schemas.user import UserRead


# ================================================================== #
# Prompt Context Models                                              #
# ================================================================== #

class PromptContext(BaseModel):
    """Structured context for prompt generation."""

    user: UserRead
    inventory_items: list[InventoryItemRead]
    appliances: list[ApplianceWithDeviceType]  # Typed instead of Any
    tools: list[KitchenToolWithDeviceType]  # Typed instead of Any
    request: RecipeGenerationRequest

    # Additional computed context
    expiring_items: list[InventoryItemRead] = Field(default_factory=list)
    low_stock_items: list[InventoryItemRead] = Field(default_factory=list)
    available_categories: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def build_from_ids(
            cls,
            db: Session,
            user_id: int,
            kitchen_id: int,
            request: RecipeGenerationRequest
    ) -> PromptContext:
        """Factory method to build context from IDs."""
        from app.crud import device as crud_device
        from app.crud import inventory as crud_inventory
        from app.crud import user as crud_user

        # CRUD calls with error handling
        user = crud_user.get_user_by_id(db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        inventory_items = crud_inventory.get_kitchen_inventory(db, kitchen_id=kitchen_id)
        appliances = crud_device.get_kitchen_appliances(db, kitchen_id=kitchen_id)
        tools = crud_device.get_kitchen_tools(db, kitchen_id=kitchen_id)

        # Compute expiring/low stock items
        expiring_items = [item for item in inventory_items if item.expires_soon]
        low_stock_items = [item for item in inventory_items if item.is_low_stock]

        # Compute available categories
        available_categories = {}
        for item in inventory_items:
            if item.food_item.category:
                category = item.food_item.category
                available_categories[category] = available_categories.get(category, 0) + 1

        return cls(
            user=user,
            inventory_items=inventory_items,
            appliances=appliances,
            tools=tools,
            request=request,
            expiring_items=expiring_items,
            low_stock_items=low_stock_items,
            available_categories=available_categories
        )


# ================================================================== #
# Recipe Generation Schemas                                          #
# ================================================================== #

class RecipeGenerationRequest(BaseModel):
    """Request schema for recipe generation."""

    cuisine_type: str | None = Field(
        default=None,
        max_length=50,
        description="Preferred cuisine type (e.g., 'Italian', 'Asian')"
    )
    meal_type: str | None = Field(
        default=None,
        max_length=30,
        description="Type of meal (e.g., 'breakfast', 'lunch', 'dinner', 'snack')"
    )
    difficulty_level: DifficultyLevel | None = Field(
        default=None,
        description="Preferred difficulty level"
    )
    max_prep_time: int | None = Field(
        default=None,
        ge=1,
        le=480,
        description="Maximum preparation time in minutes"
    )
    max_cook_time: int | None = Field(
        default=None,
        ge=1,
        le=480,
        description="Maximum cooking time in minutes"
    )
    servings: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Number of servings"
    )
    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description="List of dietary restrictions"
    )
    exclude_ingredients: list[str] = Field(
        default_factory=list,
        description="Ingredients to exclude from the recipe"
    )
    special_requests: str | None = Field(
        default=None,
        max_length=500,
        description="Any special requests or preferences"
    )

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
        """Create RecipeGenerationRequest from user input."""
        return cls(special_requests=user_input)


class RecipeGenerationResponse(BaseModel):
    """AI Response Schema - aligned with existing recipe schemas."""

    # Basic recipe info - aligned with _RecipeBase
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None)
    cuisine_type: str | None = Field(default=None, max_length=100)
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.MEDIUM)
    prep_time_minutes: int = Field(ge=0)
    cook_time_minutes: int = Field(ge=0)
    total_time_minutes: int = Field(ge=0)
    servings: int = Field(ge=1, le=20)
    tags: list[str] = Field(default_factory=list)

    # Use existing schemas directly
    ingredients: list[RecipeIngredientCreate] = Field(min_length=1)
    steps: list[RecipeStepCreate] = Field(min_length=1)
    nutrition: RecipeNutritionCreate | None = None

    # Optional AI-specific fields
    tips: list[str] = Field(default_factory=list)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        from_attributes=True
    )

    def to_recipe_create(self, created_by_user_id: int) -> RecipeCreate:
        """Convert to RecipeCreate - now with perfect alignment."""
        return RecipeCreate(
            title=self.title,
            description=self.description,
            cuisine_type=self.cuisine_type,
            prep_time_minutes=self.prep_time_minutes,
            cook_time_minutes=self.cook_time_minutes,
            total_time_minutes=self.total_time_minutes,
            difficulty=self.difficulty,
            servings=self.servings,
            tags=self.tags,
            ingredients=self.ingredients,
            steps=self.steps,
            nutrition=self.nutrition,
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