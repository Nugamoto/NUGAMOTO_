"""Pydantic schemas for kitchen input / output."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.models.kitchen import KitchenRole  # ← Import von Models!
from app.schemas.user import UserRead


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


class UserKitchenCreate(UserKitchenBase):
    """Schema used when adding a user to a kitchen."""

    user_id: int = Field(..., gt=0)


class UserKitchenUpdate(BaseModel):
    """Schema used when updating a user's role in a kitchen."""

    role: KitchenRole = Field(..., description="New role for the user in the kitchen")

    model_config = ConfigDict(from_attributes=True)


class UserKitchenRead(UserKitchenBase):
    """Schema returned to the client for user-kitchen relationships."""

    user_id: int
    kitchen_id: int
    user: UserRead


class KitchenWithUsers(KitchenRead):
    """Kitchen schema that includes related users."""

    user_kitchens: list[UserKitchenRead] = Field(default_factory=list)