from __future__ import annotations

import datetime
import logging
from typing import Any

from jose import jwt

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Warn if an insecure default secret key is used
if settings.SECRET_KEY == "CHANGE_ME_TO_A_SECURE_RANDOM_VALUE":
    logger.warning(
        "Insecure JWT SECRET_KEY is in use. Set a strong SECRET_KEY in your environment."
    )


def _now_utc() -> datetime.datetime:
    """Return the current UTC time as an aware datetime."""
    return datetime.datetime.now(datetime.timezone.utc)


def create_token(
    subject: str | int,
    *,
    token_type: str,
    expires_delta: datetime.timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT.

    Args:
        subject: The token subject (typically the user ID).
        token_type: A short label for the token purpose, e.g. "access" or "refresh".
        expires_delta: How long the token should be valid.
        extra_claims: Optional additional claims to embed into the token.

    Returns:
        The encoded JWT as a string.
    """
    now = _now_utc()
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
        user_id: int, extra_claims: dict[str, Any] | None = None
) -> str:
    """Create a short-lived access token.

    Args:
        user_id: The authenticated user's ID.
        extra_claims: Optional additional claims.

    Returns:
        Encoded access token.
    """
    return create_token(
        subject=user_id,
        token_type="access",
        expires_delta=datetime.timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        extra_claims=extra_claims,
    )


def create_refresh_token(
        user_id: int, extra_claims: dict[str, Any] | None = None
) -> str:
    """Create a long-lived refresh token.

    Args:
        user_id: The authenticated user's ID.
        extra_claims: Optional additional claims.

    Returns:
        Encoded refresh token.
    """
    return create_token(
        subject=user_id,
        token_type="refresh",
        expires_delta=datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra_claims=extra_claims,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode a JWT and return its payload.

    Args:
        token: The encoded JWT.

    Returns:
        Decoded payload as a dictionary.

    Raises:
        jose.exceptions.JWTError and its subclasses for invalid/expired tokens.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
