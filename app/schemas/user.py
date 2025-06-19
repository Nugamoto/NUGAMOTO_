"""Pydantic schemas for user input / output."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic.config import ConfigDict


class _UserBase(BaseModel):
    """Fields shared by all user-related schemas."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    diet_type: str | None = Field(default=None, max_length=50)
    allergies: str | None = Field(default=None)
    preferences: str | None = Field(default=None)

    # Allow ORM objects to be returned directly from CRUD.
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate and normalize user name."""
        if not v or v.isspace():
            raise ValueError("User name cannot be empty or whitespace")

        # Normalize to title case for consistency
        v = v.strip().title()

        if len(v) > 100:
            raise ValueError("User name must be 100 characters or less")

        return v

    @field_validator('diet_type')
    def validate_diet_type(cls, v: str | None) -> str | None:
        """Validate and normalize diet type."""
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Diet type cannot be empty or whitespace")

        # Normalize to lowercase for consistency
        return v.strip().lower()

    @field_validator('allergies', 'preferences')
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Validate and normalize text fields."""
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Text field cannot be empty or whitespace")

        return v.strip()


class UserCreate(_UserBase):
    """Schema used on **create** (request body)."""

    # No extra fields required at the moment.
    pass


class UserRead(_UserBase):
    """Schema returned to the client."""

    id: int


class UserUpdate(_UserBase):
    """Schema for partial user updates (PATCH operations)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None