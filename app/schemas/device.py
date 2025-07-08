"""Pydantic schemas for kitchen devices and tools."""

from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ================================================================== #
# Device Type Schemas                                                #
# ================================================================== #

class _DeviceTypeBase(BaseModel):
    """Base schema for device type with common fields."""

    name: Annotated[str, Field(
        min_length=1,
        max_length=100,
        description="Name of the device type"
    )]
    category: Annotated[str, Field(
        min_length=1,
        max_length=50,
        description="Device category"
    )]
    default_smart: Annotated[bool, Field(
        default=False,
        description="Whether devices of this type are typically smart"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('category')
    def validate_category(cls, v: str) -> str:
        """Validate and normalize category field."""
        if not v or v.isspace():
            raise ValueError("Category cannot be empty or whitespace")

        v_normalized = v.strip().lower()
        allowed_categories = {
            'appliance', 'tool', 'cookware', 'bakeware', 'gadget', 'storage'
        }

        if v_normalized not in allowed_categories:
            raise ValueError(f"Category must be one of: {', '.join(sorted(allowed_categories))}")

        return v_normalized

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate and normalize name field."""
        if not v or v.isspace():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()


class DeviceTypeCreate(_DeviceTypeBase):
    """Schema for creating new device type."""
    pass


class DeviceTypeUpdate(_DeviceTypeBase):
    """Schema for updating device type (partial updates allowed)."""

    name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="Name of the device type"
    )]
    category: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=50,
        description="Device category"
    )]
    default_smart: bool | None = None


class DeviceTypeRead(_DeviceTypeBase):
    """Schema for reading device type data."""

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    total_instances: int = Field(
        description="Total number of appliances and tools of this type"
    )

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Appliance Schemas                                                  #
# ================================================================== #

class _ApplianceBase(BaseModel):
    """Base schema for appliance with common fields."""

    name: Annotated[str, Field(
        min_length=1,
        max_length=255,
        description="Custom name for this appliance"
    )]
    brand: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="Manufacturer brand"
    )]
    model: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="Model number or name"
    )]
    smart: Annotated[bool, Field(
        default=False,
        description="Whether this appliance has smart/IoT capabilities"
    )]
    capacity_liters: Annotated[float | None, Field(
        None,
        gt=0,
        description="Storage or working capacity in liters"
    )]
    power_watts: Annotated[float | None, Field(
        None,
        gt=0,
        description="Power consumption in watts"
    )]
    power_kw: Annotated[float | None, Field(
        None,
        gt=0,
        description="Power consumption in kilowatts"
    )]
    year_purchased: Annotated[int | None, Field(
        None,
        ge=1900,
        le=2030,
        description="Year when the appliance was purchased"
    )]
    available: Annotated[bool, Field(
        default=True,
        description="Whether the appliance is currently available for use"
    )]
    notes: Annotated[str | None, Field(
        None,
        description="Additional notes about the appliance"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('name', 'brand', 'model', 'notes')
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Validate and normalize text fields."""
        if v is None:
            return v
        # Convert empty strings to None instead of raising validation error
        if not v or v.isspace():
            return None
        return v.strip()

    @field_validator('power_kw', 'power_watts')
    def validate_power_consistency(cls, v: float | None, info) -> float | None:
        """Validate power values and check for consistency if both are provided."""
        if v is None:
            return v

        # Basic validation - power must be positive
        if v <= 0:
            raise ValueError(f"{info.field_name} must be greater than 0")

        # Optional: Add consistency check between power_kw and power_watts
        # This would require access to other field values during validation
        # For now, we keep it simple and validate each field independently

        return v


class ApplianceCreate(_ApplianceBase):
    """Schema for creating new appliance."""

    device_type_id: Annotated[int, Field(
        gt=0,
        description="ID of the device type"
    )]


class ApplianceUpdate(_ApplianceBase):
    """Schema for updating appliance (partial updates allowed)."""

    name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=255,
        description="Custom name for this appliance"
    )]
    available: bool | None = None
    smart: bool | None = None
    power_kw: Annotated[float | None, Field(
        None,
        gt=0,
        description="Power consumption in kilowatts"
    )]


class ApplianceRead(_ApplianceBase):
    """Schema for reading appliance data."""

    id: int
    kitchen_id: int
    device_type_id: int
    display_name: str = Field(
        description="User-friendly display name"
    )
    age_years: int | None = Field(
        None,
        description="Age in years if purchase year is available"
    )
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ApplianceWithDeviceType(ApplianceRead):
    """Appliance schema with device type information."""

    device_type_name: str = Field(
        description="Name of the device type"
    )
    device_type_category: str = Field(
        description="Category of the device type"
    )


# ================================================================== #
# Kitchen Tool Schemas                                               #
# ================================================================== #

class _KitchenToolBase(BaseModel):
    """Base schema for kitchen tool with common fields."""

    name: Annotated[str, Field(
        min_length=1,
        max_length=255,
        description="Name of this kitchen tool"
    )]
    size_or_detail: Annotated[str | None, Field(
        None,
        description="Size specification or descriptive detail"
    )]
    material: Annotated[str | None, Field(
        None,
        description="Primary material"
    )]
    quantity: Annotated[int | None, Field(
        None,
        ge=1,
        le=1000,
        description="Number of identical items"
    )]
    available: Annotated[bool, Field(
        default=True,
        description="Whether the tool is currently available for use"
    )]
    notes: Annotated[str | None, Field(
        None,
        description="Additional notes about the tool"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('material')
    def validate_material(cls, v: str | None) -> str | None:
        """Validate and normalize material field."""
        if v is None:
            return v
        # Convert empty strings to None instead of raising validation error
        if not v or v.isspace():
            return None

        v_normalized = v.strip().lower()

        # Allow any material but suggest common ones
        return v_normalized

    @field_validator('name', 'size_or_detail', 'notes')
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Validate and normalize text fields."""
        if v is None:
            return v
        # Convert empty strings to None instead of raising validation error
        if not v or v.isspace():
            return None
        return v.strip()


class KitchenToolCreate(_KitchenToolBase):
    """Schema for creating new kitchen tool."""

    device_type_id: Annotated[int, Field(
        gt=0,
        description="ID of the device type"
    )]


class KitchenToolUpdate(_KitchenToolBase):
    """Schema for updating kitchen tool (partial updates allowed)."""

    name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=255,
        description="Name of this kitchen tool"
    )]
    available: bool | None = None
    quantity: Annotated[int | None, Field(
        None,
        ge=1,
        le=1000,
        description="Number of identical items"
    )]


class KitchenToolRead(_KitchenToolBase):
    """Schema for reading kitchen tool data."""

    id: int
    kitchen_id: int
    device_type_id: int
    full_description: str = Field(
        description="Comprehensive description of the tool"
    )
    is_set: bool = Field(
        description="Whether this represents multiple items"
    )
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class KitchenToolWithDeviceType(KitchenToolRead):
    """Kitchen tool schema with device type information."""

    device_type_name: str = Field(
        description="Name of the device type"
    )
    device_type_category: str = Field(
        description="Category of the device type"
    )


# ================================================================== #
# Search Parameters                                                  #
# ================================================================== #

class ApplianceSearchParams(BaseModel):
    """Parameters for filtering appliances."""

    device_type_id: int | None = Field(None, gt=0)
    brand: str | None = Field(None, min_length=1)
    smart: bool | None = None
    available: bool | None = None
    min_power_watts: float | None = Field(None, gt=0)
    max_power_watts: float | None = Field(None, gt=0)
    min_power_kw: float | None = Field(None, gt=0)
    max_power_kw: float | None = Field(None, gt=0)
    min_capacity_liters: float | None = Field(None, gt=0)
    max_capacity_liters: float | None = Field(None, gt=0)

    model_config = ConfigDict(from_attributes=True)


class KitchenToolSearchParams(BaseModel):
    """Parameters for filtering kitchen tools."""

    device_type_id: int | None = Field(None, gt=0)
    material: str | None = Field(None, min_length=1)
    available: bool | None = None
    min_quantity: int | None = Field(None, ge=1)
    is_set: bool | None = None

    model_config = ConfigDict(from_attributes=True)


# ================================================================== #
# Summary Schemas                                                    #
# ================================================================== #

class KitchenDeviceSummary(BaseModel):
    """Summary of all devices in a kitchen."""

    kitchen_id: int
    total_appliances: int = Field(description="Total number of appliances")
    total_tools: int = Field(description="Total number of kitchen tools")
    available_appliances: int = Field(description="Number of available appliances")
    available_tools: int = Field(description="Number of available tools")
    smart_appliances: int = Field(description="Number of smart appliances")
    device_types_used: int = Field(description="Number of different device types")

    model_config = ConfigDict(from_attributes=True)