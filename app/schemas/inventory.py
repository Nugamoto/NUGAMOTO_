"""Pydantic schemas for inventory input / output."""

from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.food import FoodItemRead


# ================================================================== #
# StorageLocation Schemas                                            #
# ================================================================== #

class _StorageLocationBase(BaseModel):
    """Base schema for StorageLocation with common fields."""

    name: Annotated[str, Field(
        min_length=1,
        max_length=100,
        description="Name of the storage location (e.g., 'Refrigerator', 'Pantry')"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate and normalize storage location name."""
        if not v or v.isspace():
            raise ValueError("Storage location name cannot be empty or whitespace")

        # Normalize to title case for consistency
        return v.strip().title()


class StorageLocationCreate(_StorageLocationBase):
    """Schema for creating a new storage location."""
    pass


class StorageLocationRead(_StorageLocationBase):
    """Schema for reading storage location data."""

    id: int
    kitchen_id: int

    model_config = ConfigDict(from_attributes=True)


class StorageLocationUpdate(BaseModel):
    """Schema for updating storage location data."""

    name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="Name of the storage location"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('name')
    def validate_name(cls, v: str | None) -> str | None:
        """Validate and normalize storage location name."""
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Storage location name cannot be empty or whitespace")
        
        return v.strip().title()


# ================================================================== #
# InventoryItem Schemas                                              #
# ================================================================== #

class _InventoryItemBase(BaseModel):
    """Base schema for InventoryItem with common fields."""

    food_item_id: Annotated[int, Field(
        gt=0,
        description="Food item ID being stored"
    )]
    storage_location_id: Annotated[int, Field(
        gt=0,
        description="Storage location ID where item is stored"
    )]
    quantity: Annotated[float, Field(
        ge=0.0,
        description="Quantity in the food item's base unit"
    )]
    min_quantity: Annotated[float | None, Field(
        None,
        ge=0.0,
        description="Minimum quantity threshold in base unit"
    )]
    expiration_date: Annotated[datetime.date | None, Field(
        None,
        description="Expiration date of this inventory item"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('expiration_date')
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
    """Schema for creating a new inventory item.
    
    Note: Quantities are expected to be provided in the food item's base unit.
    Future versions may support unit conversion from alternative input units.
    """
    pass


class InventoryItemRead(_InventoryItemBase):
    """Schema for reading inventory item data."""

    id: int
    kitchen_id: int
    last_updated: datetime.datetime

    # Include related objects for convenience
    food_item: FoodItemRead
    storage_location: StorageLocationRead

    # Computed properties
    is_low_stock: bool = Field(
        description="True if quantity is below min_quantity"
    )
    is_expired: bool = Field(
        description="True if expiration_date is in the past"
    )
    expires_soon: bool = Field(
        description="True if expiration_date is within configured threshold days"
    )

    # Optional unit information for display
    base_unit_name: str | None = Field(
        None,
        description="Name of the base unit for this item (from food_item.base_unit)"
    )

    model_config = ConfigDict(from_attributes=True)


class InventoryItemUpdate(_InventoryItemBase):
    """Schema for updating inventory item data."""

    food_item_id: Annotated[int | None, Field(
        None,
        gt=0,
        description="Food item ID being stored"
    )]
    storage_location_id: Annotated[int | None, Field(
        None,
        gt=0,
        description="Storage location ID where item is stored"
    )]
    quantity: Annotated[float | None, Field(
        None,
        ge=0.0,
        description="Quantity in the food item's base unit"
    )]
    min_quantity: Annotated[float | None, Field(
        None,
        ge=0.0,
        description="Minimum quantity threshold in base unit"
    )]
    expiration_date: Annotated[datetime.date | None, Field(
        None,
        description="Expiration date of this inventory item"
    )]

    @field_validator('expiration_date')
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


# ================================================================== #
# Aggregated Schemas                                                 #
# ================================================================== #

class StorageLocationWithInventory(StorageLocationRead):
    """Storage location schema that includes all inventory items."""

    inventory_items: list[InventoryItemRead] = Field(default_factory=list)


class KitchenInventorySummary(BaseModel):
    """Summary of a kitchen's complete inventory grouped by storage location."""

    kitchen_id: int
    storage_locations: list[StorageLocationWithInventory] = Field(default_factory=list)
    total_items: int = Field(
        description="Total number of inventory items"
    )
    low_stock_items: int = Field(
        description="Number of items below min_quantity"
    )
    expired_items: int = Field(
        description="Number of expired items"
    )
    expires_soon_items: int = Field(
        description="Number of items expiring within configured threshold days"
    )

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Unit Conversion Support (Future)                                   #
# ================================================================== #

class InventoryItemCreateWithConversion(BaseModel):
    """Future schema for creating inventory items with unit conversion support.
    
    This schema would allow users to input quantities in alternative units
    that would then be converted to the base unit before storage.
    """

    food_item_id: Annotated[int, Field(
        gt=0,
        description="Food item ID being stored"
    )]
    storage_location_id: Annotated[int, Field(
        gt=0,
        description="Storage location ID where item is stored"
    )]
    quantity: Annotated[float, Field(
        ge=0.0,
        description="Quantity in the specified input unit"
    )]
    input_unit_id: Annotated[int | None, Field(
        None,
        gt=0,
        description="Unit ID for input quantity (if different from base unit)"
    )]
    min_quantity: Annotated[float | None, Field(
        None,
        ge=0.0,
        description="Minimum quantity threshold"
    )]
    expiration_date: Annotated[datetime.date | None, Field(
        None,
        description="Expiration date of this inventory item"
    )]

    model_config = ConfigDict(from_attributes=True)
