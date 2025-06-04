"""Pydantic schemas for inventory input / output."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict


# ------------------------------------------------------------------ #
# FoodItem Schemas                                                   #
# ------------------------------------------------------------------ #

class _FoodItemBase(BaseModel):
    """Fields shared by all food item-related schemas."""

    name: str = Field(..., min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(default="piece", min_length=1, max_length=20)

    model_config = ConfigDict(from_attributes=True)


class FoodItemCreate(_FoodItemBase):
    """Schema used on **create** (request body)."""

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Normalize food item names to title case.
        
        Args:
            v: The name value to validate.
            
        Returns:
            The normalized name.
        """
        return v.strip().title()


class FoodItemRead(_FoodItemBase):
    """Schema returned to the client."""

    id: int


class FoodItemUpdate(_FoodItemBase):
    """Schema for partial food item updates (PATCH operations)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=20)

    @field_validator("name")
    def validate_name(cls, v: str | None) -> str | None:
        """Normalize food item names to title case.
        
        Args:
            v: The name value to validate.
            
        Returns:
            The normalized name or None.
        """
        if v is None:
            return v
        return v.strip().title()


# ------------------------------------------------------------------ #
# StorageLocation Schemas                                            #
# ------------------------------------------------------------------ #

class _StorageLocationBase(BaseModel):
    """Fields shared by all storage location-related schemas."""

    name: str = Field(..., min_length=1, max_length=100)

    model_config = ConfigDict(from_attributes=True)


class StorageLocationCreate(_StorageLocationBase):
    """Schema used on **create** (request body)."""

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        """Normalize storage location names to title case.
        
        Args:
            v: The name value to validate.
            
        Returns:
            The normalized name.
        """
        return v.strip().title()


class StorageLocationRead(_StorageLocationBase):
    """Schema returned to the client."""

    id: int
    kitchen_id: int


class StorageLocationUpdate(_StorageLocationBase):
    """Schema for partial storage location updates (PATCH operations)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("name")
    def validate_name(cls, v: str | None) -> str | None:
        """Normalize storage location names to title case.
        
        Args:
            v: The name value to validate.
            
        Returns:
            The normalized name or None.
        """
        if v is None:
            return v
        return v.strip().title()


# ------------------------------------------------------------------ #
# InventoryItem Schemas                                              #
# ------------------------------------------------------------------ #

class _InventoryItemBase(BaseModel):
    """Fields shared by all inventory item-related schemas."""

    food_item_id: int = Field(..., gt=0)
    storage_location_id: int = Field(..., gt=0)
    quantity: float = Field(..., ge=0.0)
    min_quantity: float | None = Field(default=None, ge=0.0)
    expiration_date: datetime.date | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True)

    @field_validator("expiration_date")
    def validate_expiration_date(cls, v: datetime.date | None) -> datetime.date | None:
        """Validate that expiration date is not in the past.
        
        Args:
            v: The expiration date to validate.
            
        Returns:
            The validated expiration date.
            
        Raises:
            ValueError: If the expiration date is in the past.
        """
        if v is not None and v < datetime.date.today():
            raise ValueError("Expiration date cannot be in the past")
        return v


class InventoryItemCreate(_InventoryItemBase):
    """Schema used on **create** (request body)."""
    pass


class InventoryItemRead(_InventoryItemBase):
    """Schema returned to the client."""

    id: int
    kitchen_id: int

    # Include related objects for convenience
    food_item: FoodItemRead
    storage_location: StorageLocationRead

    # Computed properties
    is_low_stock: bool = Field(..., description="True if quantity is below min_quantity")
    is_expired: bool = Field(..., description="True if expiration_date is in the past")
    expires_soon: bool = Field(..., description="True if expiration_date is within configured threshold days")


class InventoryItemUpdate(_InventoryItemBase):
    """Schema for partial inventory item updates (PATCH operations)."""

    food_item_id: int | None = Field(default=None, gt=0)
    storage_location_id: int | None = Field(default=None, gt=0)
    quantity: float | None = Field(default=None, ge=0.0)
    min_quantity: float | None = Field(default=None, ge=0.0)
    expiration_date: datetime.date | None = Field(default=None)

    @field_validator("expiration_date")
    def validate_expiration_date(cls, v: datetime.date | None) -> datetime.date | None:
        """Validate that expiration date is not in the past.
        
        Args:
            v: The expiration date to validate.
            
        Returns:
            The validated expiration date.
            
        Raises:
            ValueError: If the expiration date is in the past.
        """
        if v is not None and v < datetime.date.today():
            raise ValueError("Expiration date cannot be in the past")
        return v


# ------------------------------------------------------------------ #
# Aggregated Schemas                                                 #
# ------------------------------------------------------------------ #

class StorageLocationWithInventory(StorageLocationRead):
    """Storage location schema that includes all inventory items."""

    inventory_items: list[InventoryItemRead] = Field(default_factory=list)


class KitchenInventorySummary(BaseModel):
    """Summary of a kitchen's complete inventory grouped by storage location."""

    kitchen_id: int
    storage_locations: list[StorageLocationWithInventory] = Field(default_factory=list)
    total_items: int = Field(..., description="Total number of inventory items")
    low_stock_items: int = Field(..., description="Number of items below min_quantity")
    expired_items: int = Field(..., description="Number of expired items")
    expires_soon_items: int = Field(..., description="Number of items expiring within configured threshold days")

    model_config = ConfigDict(from_attributes=True)