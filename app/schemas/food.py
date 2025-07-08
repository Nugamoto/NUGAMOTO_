"""Pydantic schemas for food system."""

from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.core import UnitRead


# ================================================================== #
# FoodItem Schemas                                                   #
# ================================================================== #

class _FoodItemBase(BaseModel):
    """Base schema for FoodItem with common fields."""

    name: Annotated[str, Field(
        min_length=1,
        max_length=255,
        description="Name of the food item (e.g., 'Tomato', 'Rice')"
    )]
    category: Annotated[str | None, Field(
        None,
        max_length=100,
        description="Food category (e.g., 'Vegetables', 'Grains')"
    )]
    base_unit_id: Annotated[int, Field(
        gt=0,
        description="ID of the base unit for this food item"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate and normalize food item name."""
        if not v or v.isspace():
            raise ValueError("Food item name cannot be empty or whitespace")

        # Normalize to title case for consistency
        v = v.strip().title()

        if len(v) > 255:
            raise ValueError("Food item name must be 255 characters or less")

        return v

    @field_validator('category')
    def validate_category(cls, v: str | None) -> str | None:
        """Validate and normalize category."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Normalize to title case for consistency
        return v.title()


class FoodItemCreate(_FoodItemBase):
    """Schema for creating a new food item."""
    pass


class FoodItemRead(_FoodItemBase):
    """Schema for reading food item data."""

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    # Include base unit relationship for convenience
    base_unit: UnitRead | None = Field(
        None,
        description="Base unit information (populated from relationship)"
    )

    # Include base unit name for backward compatibility
    base_unit_name: str | None = Field(
        None,
        description="Name of the base unit (populated from related unit)"
    )

    model_config = ConfigDict(from_attributes=True)


class FoodItemUpdate(BaseModel):
    """Schema for updating food item data."""

    name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=255,
        description="Name of the food item"
    )]
    category: Annotated[str | None, Field(
        None,
        max_length=100,
        description="Food category"
    )]
    base_unit_id: Annotated[int | None, Field(
        None,
        gt=0,
        description="ID of the base unit for this food item"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('name')
    def validate_name(cls, v: str | None) -> str | None:
        """Validate and normalize food item name."""
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Food item name cannot be empty or whitespace")

        v = v.strip().title()

        if len(v) > 255:
            raise ValueError("Food item name must be 255 characters or less")

        return v

    @field_validator('category')
    def validate_category(cls, v: str | None) -> str | None:
        """Validate and normalize category."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        return v.title()


# ================================================================== #
# FoodItemAlias Schemas                                              #
# ================================================================== #

class _FoodItemAliasBase(BaseModel):
    """Base schema for FoodItemAlias with common fields."""

    food_item_id: Annotated[int, Field(
        gt=0,
        description="Food item ID this alias refers to"
    )]
    alias: Annotated[str, Field(
        min_length=1,
        max_length=255,
        description="Alternative name for the food item"
    )]
    user_id: Annotated[int | None, Field(
        None,
        gt=0,
        description="User who created this alias (NULL for global aliases)"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('alias')
    def validate_alias(cls, v: str) -> str:
        """Validate and normalize alias."""
        if not v or v.isspace():
            raise ValueError("Alias cannot be empty or whitespace")

        v = v.strip()
        if len(v) > 255:
            raise ValueError("Alias must be 255 characters or less")

        return v


class FoodItemAliasCreate(_FoodItemAliasBase):
    """Schema for creating a new food item alias."""
    pass


class FoodItemAliasRead(_FoodItemAliasBase):
    """Schema for reading food item alias data."""

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    # Include related information for convenience
    food_item_name: str | None = Field(
        None,
        description="Name of the food item this alias refers to"
    )
    user_name: str | None = Field(
        None,
        description="Name of the user who created this alias"
    )

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# FoodItemUnitConversion Schemas                                     #
# ================================================================== #

class _FoodItemUnitConversionBase(BaseModel):
    """Base schema for FoodItemUnitConversion with common fields."""

    food_item_id: Annotated[int, Field(
        gt=0,
        description="Food item ID this conversion applies to"
    )]
    from_unit_id: Annotated[int, Field(
        gt=0,
        description="Source unit ID for conversion"
    )]
    to_unit_id: Annotated[int, Field(
        gt=0,
        description="Target unit ID for conversion (usually base_unit)"
    )]
    factor: Annotated[float, Field(
        gt=0,
        description="Conversion factor: amount_in_from_unit * factor = amount_in_to_unit"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('to_unit_id')
    def validate_different_units(cls, v: int, info) -> int:
        """Ensure from_unit_id and to_unit_id are different."""
        if 'from_unit_id' in info.data and info.data['from_unit_id'] == v:
            raise ValueError("Cannot create conversion from a unit to itself")
        return v


class FoodItemUnitConversionCreate(_FoodItemUnitConversionBase):
    """Schema for creating a new food item unit conversion."""
    pass


class FoodItemUnitConversionRead(_FoodItemUnitConversionBase):
    """Schema for reading food item unit conversion data."""

    created_at: datetime.datetime
    updated_at: datetime.datetime

    # Include related information for convenience
    food_item_name: str | None = Field(
        None,
        description="Name of the food item"
    )
    from_unit_name: str | None = Field(
        None,
        description="Name of the source unit"
    )
    to_unit_name: str | None = Field(
        None,
        description="Name of the target unit"
    )

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Extended Schemas for API Responses                                 #
# ================================================================== #

class FoodItemWithConversions(FoodItemRead):
    """FoodItem schema including available unit conversions."""

    unit_conversions: list[FoodItemUnitConversionRead] = Field(
        default_factory=list,
        description="List of unit conversions for this food item"
    )


class FoodItemWithAliases(FoodItemRead):
    """FoodItem schema including available aliases."""

    aliases: list[FoodItemAliasRead] = Field(
        default_factory=list,
        description="List of aliases for this food item"
    )


class FoodConversionResult(BaseModel):
    """Schema for food-specific conversion calculation results."""

    food_item_id: int = Field(description="Food item ID")
    food_item_name: str = Field(description="Food item name")
    original_value: float = Field(description="Original value to convert")
    original_unit_id: int = Field(description="Original unit ID")
    original_unit_name: str = Field(description="Original unit name")
    converted_value: float = Field(description="Converted value")
    target_unit_id: int = Field(description="Target unit ID")
    target_unit_name: str = Field(description="Target unit name")
    conversion_factor: float = Field(description="Applied conversion factor")
    is_food_specific: bool = Field(
        description="True if food-specific conversion was used, False if generic unit conversion"
    )

    model_config = ConfigDict(from_attributes=True)