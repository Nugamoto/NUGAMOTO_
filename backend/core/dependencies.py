"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.security import decode_token  # import via public package API

_auth_scheme = HTTPBearer()  # default auto_error=True


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for the request lifecycle.

    This dependency provides a database session that will be automatically
    closed after the request is completed, ensuring proper cleanup.

    Yields:
        Session: SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(_auth_scheme)],
) -> int:
    """Extract and validate the current user id from the access token.

    Raises:
        HTTPException: 401 if the token is invalid, expired, or not an access token.

    Returns:
        int: Current user ID from the token subject ('sub').
    """
    try:
        token = credentials.credentials
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Not an access token")
        return int(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
