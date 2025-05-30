"""Pydantic schemas for user input / output."""

from __future__ import annotations

from typing import Union

from pydantic import BaseModel, EmailStr, Field
from pydantic.config import ConfigDict


class _UserBase(BaseModel):
    """Fields shared by all user-related schemas."""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    diet_type: Union[str, None] = Field(default=None, max_length=50)
    allergies: Union[str, None] = Field(default=None)
    preferences: Union[str, None] = Field(default=None)

    # Allow ORM objects to be returned directly from CRUD.
    model_config = ConfigDict(from_attributes=True)


class UserCreate(_UserBase):
    """Schema used on **create** (request body)."""

    # No extra fields required at the moment.
    pass


class UserRead(_UserBase):
    """Schema returned to the client."""

    id: int