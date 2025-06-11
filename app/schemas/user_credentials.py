"""Pydantic schemas for user credentials and authentication data."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCredentialsBase(BaseModel):
    """Base schema for user credentials data."""

    email: EmailStr = Field(..., description="User's email address")
    password_hash: str = Field(..., min_length=1, description="Hashed password")
    first_name: str | None = Field(None, max_length=100, description="User's first name")
    last_name: str | None = Field(None, max_length=100, description="User's last name")
    address: str | None = Field(None, description="User's street address")
    city: str | None = Field(None, max_length=100, description="User's city")
    postal_code: str | None = Field(None, max_length=20, description="User's postal/ZIP code")
    country: str | None = Field(None, max_length=100, description="User's country")
    phone: str | None = Field(None, max_length=50, description="User's phone number")

    @field_validator('email')
    def validate_email(cls, v: EmailStr) -> str:
        """Normalize email to lowercase.

        Args:
            v: Email value to validate.

        Returns:
            Normalized email address.
        """
        return str(v).lower().strip()

    @field_validator('phone')
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate phone number format.

        Args:
            v: Phone number to validate.

        Returns:
            Validated phone number.

        Raises:
            ValueError: If phone number format is invalid.
        """
        if v is None:
            return v

        # Remove common separators and spaces
        cleaned = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        # Basic validation - should contain only digits and + (for international)
        if not all(c.isdigit() or c == '+' for c in cleaned):
            raise ValueError("Phone number can only contain digits, spaces, hyphens, and + for international format")

        # Should have reasonable length (international numbers can be 7-15 digits)
        digit_count = sum(1 for c in cleaned if c.isdigit())
        if digit_count < 7 or digit_count > 15:
            raise ValueError("Phone number must have between 7 and 15 digits")

        return v.strip()

    @field_validator('postal_code')
    def validate_postal_code(cls, v: str | None) -> str | None:
        """Validate and normalize postal code.

        Args:
            v: Postal code to validate.

        Returns:
            Normalized postal code.
        """
        if v is None:
            return v
        return v.strip().upper()

    @field_validator('first_name', 'last_name', 'city', 'country')
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Validate and normalize text fields.

        Args:
            v: Text value to validate.

        Returns:
            Normalized text value.
        """
        if v is None:
            return v
        return v.strip().title()


class UserCredentialsCreate(UserCredentialsBase):
    """Schema for creating new user credentials."""

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )


class UserCredentialsUpdate(BaseModel):
    """Schema for updating existing user credentials.

    All fields are optional for partial updates.
    """

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )

    email: EmailStr | None = Field(None, description="User's email address")
    password_hash: str | None = Field(None, min_length=1, description="Hashed password")
    first_name: str | None = Field(None, max_length=100, description="User's first name")
    last_name: str | None = Field(None, max_length=100, description="User's last name")
    address: str | None = Field(None, description="User's street address")
    city: str | None = Field(None, max_length=100, description="User's city")
    postal_code: str | None = Field(None, max_length=20, description="User's postal/ZIP code")
    country: str | None = Field(None, max_length=100, description="User's country")
    phone: str | None = Field(None, max_length=50, description="User's phone number")

    @field_validator('email')
    def validate_email(cls, v: EmailStr | None) -> str | None:
        """Normalize email to lowercase."""
        return str(v).lower().strip() if v is not None else None

    @field_validator('phone')
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate phone number format."""
        if v is None:
            return v

        cleaned = v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        if not all(c.isdigit() or c == '+' for c in cleaned):
            raise ValueError("Phone number can only contain digits, spaces, hyphens, and + for international format")

        digit_count = sum(1 for c in cleaned if c.isdigit())
        if digit_count < 7 or digit_count > 15:
            raise ValueError("Phone number must have between 7 and 15 digits")

        return v.strip()

    @field_validator('postal_code')
    def validate_postal_code(cls, v: str | None) -> str | None:
        """Validate and normalize postal code."""
        return v.strip().upper() if v is not None else None

    @field_validator('first_name', 'last_name', 'city', 'country')
    def validate_text_fields(cls, v: str | None) -> str | None:
        """Validate and normalize text fields."""
        return v.strip().title() if v is not None else None


class UserCredentialsRead(UserCredentialsBase):
    """Schema for reading user credentials data."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    full_name: str | None = Field(None, description="Combined first and last name")
    full_address: str | None = Field(None, description="Formatted full address")


class UserCredentialsSummary(BaseModel):
    """Minimal schema for credentials summary."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    full_name: str | None
    city: str | None
    country: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime