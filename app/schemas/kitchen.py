
"""Pydantic schemas for kitchen input / output."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

from app.schemas.user import UserRead


class KitchenRole(str, Enum):
    """Valid roles for users in kitchens."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class _KitchenBase(BaseModel):
    """Fields shared by all kitchen-related schemas."""

    name: str = Field(..., min_length=1, max_length=255)

    # Allow ORM objects to be returned directly from CRUD.
    model_config = ConfigDict(from_attributes=True)


class KitchenCreate(_KitchenBase):
    """Schema used on **create** (request body)."""

    # No extra fields required at the moment.
    pass


class KitchenRead(_KitchenBase):
    """Schema returned to the client."""

    id: int


class KitchenUpdate(_KitchenBase):
    """Schema for partial kitchen updates (PATCH operations)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)


class UserKitchenBase(BaseModel):
    """Fields shared by all user-kitchen-related schemas."""

    role: KitchenRole = Field(..., description="Role of the user in the kitchen")

    # Allow ORM objects to be returned directly from CRUD.
    model_config = ConfigDict(from_attributes=True)

    @field_validator("role", mode="before")
    def validate_role(cls, v: str | KitchenRole) -> KitchenRole:
        """Validate that the role is one of the allowed values.

        Args:
            v: The role value to validate.

        Returns:
            The validated role.

        Raises:
            ValueError: If the role is not valid.
        """
        if isinstance(v, str):
            valid_roles = {role.value for role in KitchenRole}
            if v not in valid_roles:
                raise ValueError(
                    f"Role must be one of: {', '.join(valid_roles)}. Got: {v}"
                )
            return KitchenRole(v)
        return v


class UserKitchenCreate(UserKitchenBase):
    """Schema used when adding a user to a kitchen."""

    user_id: int = Field(..., gt=0)


class UserKitchenUpdate(BaseModel):
    """Schema used when updating a user's role in a kitchen."""

    role: KitchenRole = Field(..., description="New role for the user in the kitchen")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("role", mode="before")
    def validate_role(cls, v: str | KitchenRole) -> KitchenRole:
        """Validate that the role is one of the allowed values.
        
        Args:
            v: The role value to validate.
            
        Returns:
            The validated role.
            
        Raises:
            ValueError: If the role is not valid.
        """
        if isinstance(v, str):
            valid_roles = {role.value for role in KitchenRole}
            if v not in valid_roles:
                raise ValueError(
                    f"Role must be one of: {', '.join(valid_roles)}. Got: {v}"
                )
            return KitchenRole(v)
        return v


class UserKitchenRead(UserKitchenBase):
    """Schema returned to the client for user-kitchen relationships."""

    user_id: int
    kitchen_id: int
    user: UserRead


class KitchenWithUsers(KitchenRead):
    """Kitchen schema that includes related users."""

    user_kitchens: list[UserKitchenRead] = Field(default_factory=list)