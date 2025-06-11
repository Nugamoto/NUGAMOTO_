"""Pydantic schemas for user health profiles."""

from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _UserHealthProfileBase(BaseModel):
    """Base schema for user health profile with common fields."""

    age: Annotated[int | None, Field(
        None,
        ge=10,
        le=120,
        description="User's age in years"
    )]
    gender: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=50,
        description="User's gender"
    )]
    height_cm: Annotated[int | None, Field(
        None,
        ge=50,
        le=300,
        description="User's height in centimeters"
    )]
    weight_kg: Annotated[float | None, Field(
        None,
        ge=20.0,
        le=500.0,
        description="User's weight in kilograms"
    )]
    activity_level: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's activity level"
    )]
    health_conditions: Annotated[str | None, Field(
        None,
        min_length=1,
        description="Health conditions and medical notes"
    )]
    goal: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=200,
        description="Health and fitness goals"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('gender')
    def validate_gender(cls, v: str | None) -> str | None:
        """Validate and normalize gender field.
        
        Args:
            v: Raw gender input or None.
            
        Returns:
            Normalized gender (lowercase) or None.
            
        Raises:
            ValueError: If gender is not in allowed values.
        """
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Gender cannot be empty or whitespace")

        v_normalized = v.strip().lower()
        allowed_genders = {
            'male', 'female', 'non-binary', 'prefer not to say', 'other'
        }

        if v_normalized not in allowed_genders:
            raise ValueError(f"Gender must be one of: {', '.join(sorted(allowed_genders))}")

        return v_normalized

    @field_validator('activity_level')
    def validate_activity_level(cls, v: str | None) -> str | None:
        """Validate and normalize activity level field.
        
        Args:
            v: Raw activity level input or None.
            
        Returns:
            Normalized activity level (lowercase) or None.
            
        Raises:
            ValueError: If activity level is not in allowed values.
        """
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Activity level cannot be empty or whitespace")

        v_normalized = v.strip().lower()
        allowed_levels = {
            'sedentary', 'lightly active', 'moderately active',
            'very active', 'extremely active'
        }

        if v_normalized not in allowed_levels:
            raise ValueError(f"Activity level must be one of: {', '.join(sorted(allowed_levels))}")

        return v_normalized

    @field_validator('health_conditions', 'goal')
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Validate and normalize text fields.
        
        Args:
            v: Raw text input or None.
            
        Returns:
            Normalized text (trimmed) or None.
        """
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Text field cannot be empty or whitespace")

        return v.strip()


class UserHealthProfileCreate(_UserHealthProfileBase):
    """Schema for creating new user health profile."""
    pass


class UserHealthProfileUpdate(_UserHealthProfileBase):
    """Schema for updating existing user health profile (partial updates allowed)."""
    pass


class UserHealthProfileRead(_UserHealthProfileBase):
    """Schema for reading user health profile data with complete information."""

    id: int
    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    bmi: float | None = Field(
        None,
        description="Calculated Body Mass Index"
    )
    is_complete: bool = Field(
        description="Whether profile has all essential data for AI recommendations"
    )

    model_config = ConfigDict(from_attributes=True)


class UserHealthProfileSummary(BaseModel):
    """Schema for compact user health profile summary."""

    id: int
    user_id: int
    age: int | None = Field(
        None,
        description="User's age in years"
    )
    gender: str | None = Field(
        None,
        description="User's gender"
    )
    bmi: float | None = Field(
        None,
        description="Calculated Body Mass Index"
    )
    activity_level: str | None = Field(
        None,
        description="User's activity level"
    )
    goal: str | None = Field(
        None,
        description="Health and fitness goals"
    )
    is_complete: bool = Field(
        description="Whether profile has all essential data"
    )
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
