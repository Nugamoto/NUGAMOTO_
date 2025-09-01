"""FastAPI router exposing the users endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db, get_current_user_id, require_same_user
from backend.crud import user as crud_user
from backend.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


# ================================================================== #
# User Endpoints                                                     #
# ================================================================== #

@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user_id)],
)
def create_user(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_data: UserCreate,
) -> UserRead:
    """Create a new user.

    Args:
        db: Database session
        user_data: User creation data

    Returns:
        Created user data

    Raises:
        HTTPException: 400 if email already registered
    """
    existing_user = crud_user.get_user_by_email(db=db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        return crud_user.create_user(db=db, user_data=user_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )


@router.get(
    "/",
    response_model=list[UserRead],
    dependencies=[Depends(get_current_user_id)],
)
def get_users(
        *,
        db: Annotated[Session, Depends(get_db)],
        skip: int = 0,
        limit: int = 100,
) -> list[UserRead]:
    """Get all users.

    Args:
        db: Database session
        skip: Number of users to skip
        limit: Maximum number of users to return

    Returns:
        List of users
    """
    return crud_user.get_all_users(db=db, skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_same_user)],
)
def get_user_by_id(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_id: int,
) -> UserRead:
    """Get user by ID.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User data

    Raises:
        HTTPException: 404 if user not found
    """
    user = crud_user.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    return user


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_same_user)],
)
def update_user(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_id: int,
        user_data: UserUpdate,
) -> UserRead:
    """Update an existing user with partial data (PATCH operation).

    Only the fields provided in the request body will be updated.

    Args:
        db: Database session
        user_id: Primary key of the user to update
        user_data: Partial user data containing only fields to be updated

    Returns:
        The updated user with all current field values

    Raises:
        HTTPException:
            * 404 – if the user does not exist
            * 400 – if another user already has the email address
    """
    try:
        updated_user = crud_user.update_user(db=db, user_id=user_id, user_data=user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        return updated_user
    except ValueError as exc:
        if "Email is already taken" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{user_id}",
    dependencies=[Depends(require_same_user)],
)
def delete_user(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_id: int,
) -> Response:
    """Delete a user by primary key.

    Args:
        db: Database session
        user_id: ID of the user to delete

    Returns:
        Empty response with 204 status

    Raises:
        HTTPException: 404 if the user does not exist
    """
    success = crud_user.delete_user(db=db, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Additional User Endpoints                                          #
# ================================================================== #

@router.get(
    "/by-email/{email}",
    response_model=UserRead,
    dependencies=[Depends(get_current_user_id)],
)
def get_user_by_email(
        *,
        db: Annotated[Session, Depends(get_db)],
        email: str,
        current_user_id: int = Depends(get_current_user_id),
) -> UserRead:
    """Get user by email address (only your own account).

    Prevents leaking existence of other users' emails.
    """
    user = crud_user.get_user_by_email(db=db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found",
        )

    if getattr(user, "id", None) != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this resource",
        )

    return user