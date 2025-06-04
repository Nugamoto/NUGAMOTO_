"""Pydantic schemas for shopping system."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.core.enums import PackageType, ShoppingListType


# ================================================================== #
# Shopping List Schemas                                              #
# ================================================================== #

class _ShoppingListBase(BaseModel):
    """Fields shared by all shopping list schemas."""

    name: str = Field(..., min_length=1, max_length=255)
    type: ShoppingListType

    model_config = ConfigDict(from_attributes=True)


class ShoppingListCreate(_ShoppingListBase):
    """Schema for creating a new shopping list."""

    kitchen_id: int = Field(..., gt=0)


class ShoppingListRead(_ShoppingListBase):
    """Schema returned to the client."""

    id: int
    kitchen_id: int
    created_at: datetime


class ShoppingListUpdate(BaseModel):
    """Schema for updating shopping list."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: ShoppingListType | None = None

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Shopping Product Schemas                                           #
# ================================================================== #

class _ShoppingProductBase(BaseModel):
    """Fields shared by all shopping product schemas."""

    food_item_id: int = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    quantity: float = Field(..., gt=0)
    package_type: PackageType
    estimated_price: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(from_attributes=True)


class ShoppingProductCreate(_ShoppingProductBase):
    """Schema for creating a new shopping product."""
    pass


class ShoppingProductRead(_ShoppingProductBase):
    """Schema returned to the client."""

    id: int
    created_at: datetime

    # Optional nested food item details
    food_item: dict | None = None


class ShoppingProductUpdate(BaseModel):
    """Schema for updating shopping product."""

    unit: str | None = Field(default=None, min_length=1, max_length=20)
    quantity: float | None = Field(default=None, gt=0)
    package_type: PackageType | None = None
    estimated_price: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Shopping Product Assignment Schemas                               #
# ================================================================== #

class _ShoppingProductAssignmentBase(BaseModel):
    """Fields shared by assignment schemas."""

    added_by_user_id: int | None = Field(default=None, gt=0)
    is_auto_added: bool = False
    note: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class ShoppingProductAssignmentCreate(_ShoppingProductAssignmentBase):
    """Schema for assigning a product to a list."""

    shopping_product_id: int = Field(..., gt=0)


class ShoppingProductAssignmentRead(_ShoppingProductAssignmentBase):
    """Schema returned to client with full product details."""

    shopping_list_id: int
    shopping_product_id: int
    created_at: datetime

    # Nested product details
    shopping_product: ShoppingProductRead


class ShoppingProductAssignmentUpdate(BaseModel):
    """Schema for updating assignment."""

    note: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Search Parameters                                                 #
# ================================================================== #

class ShoppingProductSearchParams(BaseModel):
    """Parameters for filtering shopping products."""

    food_item_id: int | None = None
    package_type: PackageType | None = None
    min_price: float | None = None
    max_price: float | None = None
    unit: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ShoppingProductAssignmentSearchParams(BaseModel):
    """Parameters for filtering product assignments."""

    is_auto_added: bool | None = None
    added_by_user_id: int | None = None
    food_item_id: int | None = None
    package_type: PackageType | None = None

    model_config = ConfigDict(from_attributes=True)
