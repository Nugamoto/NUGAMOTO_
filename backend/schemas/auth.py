from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login payload with user credentials."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=1, description="User password (plain)")


class TokenPair(BaseModel):
    """Token response containing access and refresh tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"