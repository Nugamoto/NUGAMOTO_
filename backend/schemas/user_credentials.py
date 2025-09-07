"""Pydantic schemas for user credentials and authentication data."""

from __future__ import annotations

import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _UserCredentialsBase(BaseModel):
    """Base schema for user credentials with common fields."""

    password_hash: Annotated[str, Field(
        min_length=1,
        max_length=255,
        description="Hashed password for authentication"
    )]
    first_name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's first name"
    )]
    last_name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's last name"
    )]
    address: Annotated[str | None, Field(
        None,
        min_length=1,
        description="User's street address"
    )]
    city: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's city"
    )]
    postal_code: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=20,
        description="User's postal/ZIP code"
    )]
    country: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's country"
    )]
    phone: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=50,
        description="User's phone number"
    )]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        from_attributes=True
    )

    @field_validator('phone')
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate and normalize phone number format.

        Args:
            v: Raw phone number input or None.

        Returns:
            Normalized phone number or None.

        Raises:
            ValueError: If phone number format is invalid.
        """
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Phone number cannot be empty or whitespace")

        v = v.strip()
        cleaned = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        if not all(c.isdigit() or c == '+' for c in cleaned):
            raise ValueError("Phone number can only contain digits, spaces, hyphens, parentheses, and + for international format")

        digit_count = sum(1 for c in cleaned if c.isdigit())
        if digit_count < 7 or digit_count > 15:
            raise ValueError("Phone number must have between 7 and 15 digits")

        return v

    @field_validator('postal_code')
    def validate_postal_code(cls, v: str | None) -> str | None:
        """Validate and normalize postal code format.

        Args:
            v: Raw postal code input or None.

        Returns:
            Normalized postal code (uppercase, trimmed) or None.
        """
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Postal code cannot be empty or whitespace")

        return v.strip().upper()

    @field_validator('first_name', 'last_name', 'city', 'country')
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Validate and normalize text fields with title case.

        Args:
            v: Raw text input or None.

        Returns:
            Normalized text (title case, trimmed) or None.
        """
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Text field cannot be empty or whitespace")

        return v.strip().title()

    @field_validator('address')
    def validate_address(cls, v: str | None) -> str | None:
        """Validate and normalize address field.

        Args:
            v: Raw address input or None.

        Returns:
            Normalized address (trimmed) or None.
        """
        if v is None:
            return v

        if not v or v.isspace():
            raise ValueError("Address cannot be empty or whitespace")

        return v.strip()


class UserCredentialsCreate(_UserCredentialsBase):
    """Schema for creating new user credentials."""
    pass


class UserCredentialsUpdate(_UserCredentialsBase):
    """Schema for updating existing user credentials (partial updates allowed)."""

    # Override fields to make them optional
    password_hash: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=255,
        description="Hashed password for authentication"
    )]
    first_name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's first name"
    )]
    last_name: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's last name"
    )]
    address: Annotated[str | None, Field(
        None,
        min_length=1,
        description="User's street address"
    )]
    city: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's city"
    )]
    postal_code: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=20,
        description="User's postal/ZIP code"
    )]
    country: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=100,
        description="User's country"
    )]
    phone: Annotated[str | None, Field(
        None,
        min_length=1,
        max_length=50,
        description="User's phone number"
    )]

    # Validators are inherited automatically


class UserCredentialsRead(_UserCredentialsBase):
    """Schema for reading user credentials data with complete information."""

    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    full_name: str | None = Field(
        None,
        description="Combined first and last name"
    )
    full_address: str | None = Field(
        None,
        description="Formatted full address"
    )

    model_config = ConfigDict(from_attributes=True)


class UserCredentialsSummary(BaseModel):
    """Schema for compact user credentials summary."""

    user_id: int
    full_name: str | None = Field(
        None,
        description="Combined first and last name"
    )
    city: str | None = Field(
        None,
        description="User's city"
    )
    country: str | None = Field(
        None,
        description="User's country"
    )
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)