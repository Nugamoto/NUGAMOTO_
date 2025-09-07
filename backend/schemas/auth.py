from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login payload with user credentials."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=1, description="User password (plain)")


class RegisterRequest(BaseModel):
    """Registration payload for creating a new account."""
    name: str = Field(..., min_length=1, max_length=100, description="Display name")
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, max_length=256, description="User password (plain)")


class TokenPair(BaseModel):
    """Token response containing access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"