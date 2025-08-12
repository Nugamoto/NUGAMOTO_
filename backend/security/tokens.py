from __future__ import annotations

import datetime
from typing import Any

from jose import jwt

class JWTSettings:
    """JWT configuration."""
    SECRET_KEY: str = "CHANGE_ME_TO_A_SECURE_RANDOM_VALUE"  # load from env in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14


def create_token(
    subject: str | int,
    *,
    token_type: str,
    expires_delta: datetime.timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, JWTSettings.SECRET_KEY, algorithm=JWTSettings.ALGORITHM)


def create_access_token(user_id: int, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a short-lived access token."""
    return create_token(
        subject=user_id,
        token_type="access",
        expires_delta=datetime.timedelta(minutes=JWTSettings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims=extra_claims,
    )


def create_refresh_token(user_id: int, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a long-lived refresh token."""
    return create_token(
        subject=user_id,
        token_type="refresh",
        expires_delta=datetime.timedelta(days=JWTSettings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra_claims=extra_claims,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode a JWT and return payload (raises on failure)."""
    return jwt.decode(token, JWTSettings.SECRET_KEY, algorithms=[JWTSettings.ALGORITHM])