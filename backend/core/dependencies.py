"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.enums import KitchenRole
from backend.crud import kitchen as crud_kitchen
from backend.crud import recipe as crud_recipe
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


def require_super_admin(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(_auth_scheme)],
) -> None:
    """Ensure the caller has a global admin/superadmin privilege.

    Supported token claims (any one is sufficient):
      - is_superadmin: true
      - is_admin: true
      - role: "superadmin" or "admin"
      - permissions: contains "users:create"

    Raise 403 otherwise.
    """
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise ValueError("Not an access token")

        is_superadmin = bool(payload.get("is_superadmin"))
        is_admin = bool(payload.get("is_admin"))
        role = str(payload.get("role", "") or "").lower()
        perms = payload.get("permissions") or []
        if isinstance(perms, str):
            perms = [perms]

        allowed_by_role = role in {"superadmin", "admin"}
        allowed_by_perm = "users:create" in {str(p).lower() for p in perms}

        if not (is_superadmin or is_admin or allowed_by_role or allowed_by_perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


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

    return checker


def require_kitchen_member():
    """Shortcut: requires membership in the kitchen (any role)."""
    return require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN, KitchenRole.MEMBER})


def require_same_user(
        user_id: int,
        current_user_id: Annotated[int, Depends(get_current_user_id)],
) -> None:
    """Ensure the path user_id matches the authenticated user."""
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this resource",
        )


def require_recipe_owner_or_admin(
        recipe_id: int,
        current_user_id: Annotated[int, Depends(get_current_user_id)],
        db: Annotated[Session, Depends(get_db)],
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(_auth_scheme)] = None,
) -> None:
    """Ensure current user is the recipe owner or has admin privileges.

    Expects:
        - Path parameter: recipe_id: int
        - Recipe exists with created_by_user_id set.

    Behavior:
        - Allows if recipe.created_by_user_id == current_user_id
        - Otherwise, allows if token has admin claims (same logic as require_super_admin)
        - Raises 404 if recipe doesn't exist
        - Raises 403 otherwise
    """
    # Fetch owner
    recipe_orm = crud_recipe.get_recipe_orm_by_id(db, recipe_id)
    if not recipe_orm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")

    if getattr(recipe_orm, "created_by_user_id", None) == current_user_id:
        return

    # Fallback to admin claim check (inline to avoid double-decoding in require_super_admin)
    try:
        payload = decode_token(credentials.credentials)
        is_superadmin = bool(payload.get("is_superadmin"))
        is_admin = bool(payload.get("is_admin"))
        role = str(payload.get("role", "") or "").lower()
        perms = payload.get("permissions") or []
        if isinstance(perms, str):
            perms = [perms]
        allowed_by_role = role in {"superadmin", "admin"}
        allowed_by_perm = "users:create" in {str(p).lower() for p in perms}
        if is_superadmin or is_admin or allowed_by_role or allowed_by_perm:
            return
    except Exception:
        pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the recipe owner or an admin may perform this action",
    )
