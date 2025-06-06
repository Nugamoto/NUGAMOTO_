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
        validate_assignment=True
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate unit name."""
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


class UnitRead(_UnitBase):
    """Schema for reading unit data."""

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
        validate_assignment=True
    )

    @field_validator('to_unit_id')
    @classmethod
    def validate_different_units(cls, v: int, info) -> int:
        """Ensure from_unit_id and to_unit_id are different."""
        if 'from_unit_id' in info.data and info.data['from_unit_id'] == v:
            raise ValueError("Cannot create conversion from a unit to itself")
        return v


class UnitConversionCreate(_UnitConversionBase):
    """Schema for creating a new unit conversion."""
    pass


class UnitConversionRead(_UnitConversionBase):
    """Schema for reading unit conversion data."""

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
    """Unit schema including available conversions."""

    available_conversions: list[UnitConversionRead] = Field(
        default_factory=list,
        description="List of conversions from this unit"
    )


class ConversionResult(BaseModel):
    """Schema for conversion calculation results."""

    original_value: float = Field(description="Original value to convert")
    original_unit_id: int = Field(description="Original unit ID")
    original_unit_name: str = Field(description="Original unit name")
    converted_value: float = Field(description="Converted value")
    target_unit_id: int = Field(description="Target unit ID")
    target_unit_name: str = Field(description="Target unit name")
    conversion_factor: float = Field(description="Applied conversion factor")

    model_config = ConfigDict(from_attributes=True)