"""User related Pydantic schemas."""

from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, EmailStr


class UserBase(BaseModel):
    """Base user schema with common fields."""

    name: Annotated[str, Field(
        min_length=2,
        max_length=100,
        description="Name of the user"
    )]
    email: EmailStr = Field(description="Email address")
    diet_type: Annotated[str | None, Field(
        None,
        max_length=50,
        description="Dietary type preference"
    )]
    allergies: Annotated[str | None, Field(
        None,
        max_length=500,
        description="User allergies information"
    )]
    preferences: Annotated[str | None, Field(
        None,
        max_length=500,
        description="User food preferences"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate name field."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @field_validator('allergies', 'preferences', 'diet_type')
    def validate_optional_text_fields(cls, v: str | None) -> str | None:
        """Validate optional text fields - allow empty strings by converting to None."""
        if v is None:
            return None
        # Convert empty strings to None for cleaner data
        if not v.strip():
            return None
        return v.strip()


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    name: Annotated[str | None, Field(
        None,
        min_length=2,
        max_length=100,
        description="Name of the user"
    )]
    email: EmailStr | None = Field(None, description="Email address")
    diet_type: Annotated[str | None, Field(
        None,
        max_length=50,
        description="Dietary type preference"
    )]
    allergies: Annotated[str | None, Field(
        None,
        max_length=500,
        description="User allergies information"
    )]
    preferences: Annotated[str | None, Field(
        None,
        max_length=500,
        description="User food preferences"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('name')
    def validate_name(cls, v: str | None) -> str | None:
        """Validate name field when provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty or whitespace when provided")
        return v.strip() if v else None

    @field_validator('allergies', 'preferences', 'diet_type')
    def validate_optional_text_fields(cls, v: str | None) -> str | None:
        """Validate optional text fields - allow empty strings by converting to None."""
        if v is None:
            return None
        # Convert empty strings to None for cleaner data
        if not v.strip():
            return None
        return v.strip()


class UserRead(UserBase):
    """Schema for reading user data."""

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UserSummary(BaseModel):
    """Schema for user statistics summary."""

    total_users: int
    users_by_diet_type: dict[str, int]
    users_with_allergies: int
    users_with_preferences: int

    model_config = ConfigDict(from_attributes=True)
