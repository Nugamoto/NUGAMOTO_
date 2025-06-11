"""Pydantic schemas for user health profiles."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserHealthProfileBase(BaseModel):
    """Base schema for user health profile data."""

    age: int | None = Field(None, ge=0, le=150, description="User's age in years")
    gender: str | None = Field(None, max_length=50, description="User's gender")
    height_cm: int | None = Field(None, gt=0, le=300, description="User's height in centimeters")
    weight_kg: float | None = Field(None, gt=0, le=1000, description="User's weight in kilograms")
    activity_level: str | None = Field(None, max_length=100, description="User's activity level")
    health_conditions: str | None = Field(None, description="User's health conditions and medical notes")
    goal: str | None = Field(None, max_length=200, description="User's health/fitness goals")

    @field_validator('gender')
    def validate_gender(cls, v: str | None) -> str | None:
        """Validate gender field.

        Args:
            v: Gender value to validate.

        Returns:
            Validated gender value.

        Raises:
            ValueError: If gender is not in allowed values.
        """
        if v is None:
            return v

        allowed_genders = {
            'male', 'female', 'non-binary', 'prefer not to say', 'other'
        }
        if v.lower() not in allowed_genders:
            raise ValueError(f"Gender must be one of: {', '.join(allowed_genders)}")
        return v.lower()

    @field_validator('activity_level')
    def validate_activity_level(cls, v: str | None) -> str | None:
        """Validate activity level field.

        Args:
            v: Activity level value to validate.

        Returns:
            Validated activity level value.

        Raises:
            ValueError: If activity level is not in allowed values.
        """
        if v is None:
            return v

        allowed_levels = {
            'sedentary', 'lightly active', 'moderately active',
            'very active', 'extremely active'
        }
        if v.lower() not in allowed_levels:
            raise ValueError(f"Activity level must be one of: {', '.join(allowed_levels)}")
        return v.lower()


class UserHealthProfileCreate(UserHealthProfileBase):
    """Schema for creating a new user health profile."""
    pass


class UserHealthProfileUpdate(UserHealthProfileBase):
    """Schema for updating an existing user health profile.

    All fields are optional for partial updates.
    """
    pass


class UserHealthProfileRead(UserHealthProfileBase):
    """Schema for reading user health profile data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    last_updated: datetime.datetime
    bmi: float | None = Field(None, description="Calculated Body Mass Index")
    is_complete: bool = Field(description="Whether profile has all essential data")


class UserHealthProfileSummary(BaseModel):
    """Minimal schema for health profile summary."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    age: int | None
    gender: str | None
    bmi: float | None
    activity_level: str | None
    goal: str | None
    is_complete: bool
    last_updated: datetime.datetime
