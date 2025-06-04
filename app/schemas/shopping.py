"""Pydantic schemas for shopping list functionality."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.models.shopping import ShoppingListType, PackageType


class _ShoppingListBase(BaseModel):
    """Base schema for shopping list validation."""

    kitchen_id: int = Field(..., gt=0, description="ID of the kitchen this list belongs to")
    name: str = Field(..., min_length=1, max_length=255, description="Name of the shopping list")
    type: ShoppingListType = Field(..., description="Type of shopping destination")

    model_config = ConfigDict(from_attributes=True)


class ShoppingListCreate(_ShoppingListBase):
    """Schema for creating new shopping lists."""
    pass


class ShoppingListRead(_ShoppingListBase):
    """Schema for reading shopping lists."""

    id: int = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")


class ShoppingListUpdate(BaseModel):
    """Schema for updating shopping lists."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="Name of the shopping list")
    type: ShoppingListType | None = Field(default=None, description="Type of shopping destination")

    model_config = ConfigDict(from_attributes=True)


class _ShoppingListItemBase(BaseModel):
    """Base schema for shopping list item validation."""

    food_item_id: int = Field(..., gt=0, description="ID of the food item")
    quantity: float = Field(..., gt=0, description="Quantity needed")
    unit: str = Field(..., min_length=1, max_length=50, description="Unit of measurement")
    package_type: PackageType | None = Field(default=None, description="Type of packaging")
    estimated_price: float | None = Field(default=None, ge=0, description="Estimated price in euros")
    is_auto_added: bool = Field(default=False, description="Whether item was added automatically")
    added_by_user_id: int | None = Field(default=None, gt=0, description="ID of user who added the item manually")

    model_config = ConfigDict(from_attributes=True)


class ShoppingListItemCreate(_ShoppingListItemBase):
    """Schema for creating new shopping list items."""
    pass


class ShoppingListItemRead(_ShoppingListItemBase):
    """Schema for reading shopping list items."""

    id: int = Field(..., description="Unique identifier")
    shopping_list_id: int = Field(..., description="ID of the shopping list")
    created_at: datetime = Field(..., description="Creation timestamp")


class ShoppingListItemUpdate(BaseModel):
    """Schema for updating shopping list items."""

    quantity: float | None = Field(default=None, gt=0, description="Quantity needed")
    unit: str | None = Field(default=None, min_length=1, max_length=50, description="Unit of measurement")
    package_type: PackageType | None = Field(default=None, description="Type of packaging")
    estimated_price: float | None = Field(default=None, ge=0, description="Estimated price in euros")
    is_auto_added: bool | None = Field(default=None, description="Whether item was added automatically")
    added_by_user_id: int | None = Field(default=None, gt=0, description="ID of user who added the item manually")

    model_config = ConfigDict(from_attributes=True)


class ShoppingListWithItems(ShoppingListRead):
    """Shopping list schema that includes all items."""

    items: list[ShoppingListItemRead] = Field(default_factory=list, description="Items in the shopping list")


class ShoppingListItemSearchParams(BaseModel):
    """Schema for shopping list item search and filtering parameters."""

    is_auto_added: bool | None = Field(default=None, description="Filter by auto-added status")
    added_by_user_id: int | None = Field(default=None, gt=0, description="Filter by user who added the item")
    food_item_id: int | None = Field(default=None, gt=0, description="Filter by food item")
    package_type: PackageType | None = Field(default=None, description="Filter by package type")
    min_price: float | None = Field(default=None, ge=0, description="Minimum estimated price")
    max_price: float | None = Field(default=None, ge=0, description="Maximum estimated price")

    model_config = ConfigDict(from_attributes=True)


class ShoppingListSummary(BaseModel):
    """Schema for shopping list statistics summary."""

    total_lists: int = Field(..., description="Total number of shopping lists")
    total_items: int = Field(..., description="Total number of items across all lists")
    items_by_type: dict[str, int] = Field(..., description="Count by shopping list type")
    auto_added_items: int = Field(..., description="Number of auto-added items")
    manual_items: int = Field(..., description="Number of manually added items")
    total_estimated_value: float = Field(..., description="Total estimated value of all items")

    model_config = ConfigDict(from_attributes=True)
