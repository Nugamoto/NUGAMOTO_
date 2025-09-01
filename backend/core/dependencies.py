"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.enums import KitchenRole
from backend.crud import kitchen as crud_kitchen
from backend.crud import user as crud_user
from backend.db.session import SessionLocal
from backend.security import decode_token

_auth_scheme = HTTPBearer()


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


def get_current_user(
        user_id: Annotated[int, Depends(get_current_user_id)],
        db: Annotated[Session, Depends(get_db)],
):
    """Load and return the current user (schema)."""
    user = crud_user.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def require_kitchen_role(required_roles: set[KitchenRole]):
    """Dependency factory enforcing a required role set within a kitchen.

    Usage:
        @router.post(..., dependencies=[Depends(require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN}))])

    Expects:
        - Path parameter: kitchen_id: int
        - Uses: crud_kitchen.get_user_kitchen_relationship(db, kitchen_id, user_id)
                and checks the 'role' field on the returned schema.
    """


    def checker(
            kitchen_id: int,
            user_id: Annotated[int, Depends(get_current_user_id)],
            db: Annotated[Session, Depends(get_db)],
    ) -> None:
        rel = crud_kitchen.get_user_kitchen_relationship(db, kitchen_id=kitchen_id, user_id=user_id)
        if rel is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this kitchen",
            )

        # rel is a UserKitchenRead schema; it should expose 'role'
        role_value = getattr(rel, "role", None)
        try:
            role = KitchenRole(role_value) if role_value is not None else None
        except ValueError:
            role = None

        if role is None or role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this action",
            )
        # If ok, the dependency returns None and allows the request to proceed.


    return checker


def require_kitchen_member():
    """Shortcut: requires membership in the kitchen (any role)."""
    return require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN, KitchenRole.MEMBER})
