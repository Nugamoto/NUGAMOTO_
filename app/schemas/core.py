"""Pydantic schemas for core unit system."""

from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.core import UnitType


# ================================================================== #
# Unit Schemas                                                       #
# ================================================================== #

class _UnitBase(BaseModel):
    """Base schema for Unit with common fields."""

    name: Annotated[str, Field(
        min_length=1,
        max_length=50,
        description="Unit name (e.g., 'g', 'ml', 'piece', 'pack')"
    )]
    type: Annotated[UnitType, Field(
        description="Unit type: weight, volume, count, measure, or package"
    )]
    to_base_factor: Annotated[float, Field(
        gt=0,
        description="Factor to convert to base unit (e.g., 1000 for kg → g)"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('name')
    def validate_name(cls, v: str | None) -> str | None:
        """Validate and normalize unit name if provided.
        
        Args:
            v: Raw unit name input (can be None for updates).
            
        Returns:
            Normalized unit name (lowercase, trimmed) or None.
            
        Raises:
            ValueError: If name is empty, whitespace only, or too long.
        """
        if v is None:
            return v
            
        if not v or v.isspace():
            raise ValueError("Unit name cannot be empty or whitespace")

        # Remove extra whitespace and convert to lowercase for consistency
        v = v.strip().lower()

        # Basic validation for common unit patterns
        if len(v) > 50:
            raise ValueError("Unit name must be 50 characters or less")

        return v


class UnitCreate(_UnitBase):
    """Schema for creating a new unit."""
    pass


class UnitUpdate(_UnitBase):
    """Schema for updating an existing unit (partial updates allowed)."""

    # Override fields to make them optional
    name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=50,
        description="Unit name (e.g., 'g', 'ml', 'piece', 'pack')"
    )]
    type: Annotated[UnitType | None, Field(
        None,
        description="Unit type: weight, volume, count, measure, or package"
    )]
    to_base_factor: Annotated[float | None, Field(
        None,
        gt=0,
        description="Factor to convert to base unit (e.g., 1000 for kg → g)"
    )]

    # Validator is inherited automatically - no duplication!


class UnitRead(_UnitBase):
    """Schema for reading unit data with complete information."""

    id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Unit Conversion Schemas                                            #
# ================================================================== #

class _UnitConversionBase(BaseModel):
    """Base schema for UnitConversion with common fields."""

    from_unit_id: Annotated[int, Field(
        gt=0,
        description="Source unit ID for conversion"
    )]
    to_unit_id: Annotated[int, Field(
        gt=0,
        description="Target unit ID for conversion"
    )]
    factor: Annotated[float, Field(
        gt=0,
        description="Conversion factor: value_in_from_unit * factor = value_in_to_unit"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('to_unit_id')
    def validate_different_units(cls, v: int, info) -> int:
        """Ensure from_unit_id and to_unit_id are different.
        
        Args:
            v: Target unit ID.
            info: Validation info containing other field values.
            
        Returns:
            Validated target unit ID.
            
        Raises:
            ValueError: If attempting to create self-conversion.
        """
        if 'from_unit_id' in info.data and info.data['from_unit_id'] == v:
            raise ValueError("Cannot create conversion from a unit to itself")
        return v


class UnitConversionCreate(_UnitConversionBase):
    """Schema for creating a new unit conversion relationship."""
    pass


class UnitConversionUpdate(BaseModel):
    """Schema for updating an existing unit conversion (only factor can be updated)."""

    factor: Annotated[float, Field(
        gt=0,
        description="New conversion factor: value_in_from_unit * factor = value_in_to_unit"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )


class UnitConversionRead(_UnitConversionBase):
    """Schema for reading unit conversion data with related unit names."""

    # Include related unit information for convenience
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

class UnitWithConversions(UnitRead):
    """Unit schema including all available conversions from this unit."""

    available_conversions: list[UnitConversionRead] = Field(
        default_factory=list,
        description="List of all possible conversions from this unit"
    )

    model_config = ConfigDict(from_attributes=True)


class ConversionResult(BaseModel):
    """Schema for unit conversion calculation results."""

    original_value: float = Field(
        description="Original numeric value that was converted"
    )
    original_unit_id: int = Field(
        description="Source unit identifier"
    )
    original_unit_name: str = Field(
        description="Human-readable source unit name"
    )
    converted_value: float = Field(
        description="Result of the conversion calculation"
    )
    target_unit_id: int = Field(
        description="Target unit identifier"
    )
    target_unit_name: str = Field(
        description="Human-readable target unit name"
    )
    conversion_factor: float = Field(
        description="Conversion factor that was applied in the calculation"
    )

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Validation Schemas                                                 #
# ================================================================== #

class ConversionPossibilityCheck(BaseModel):
    """Schema for checking if conversion between units is possible."""

    can_convert: bool = Field(
        description="Whether conversion between the specified units is possible"
    )
    
    model_config = ConfigDict(from_attributes=True)
