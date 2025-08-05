"""FastAPI router exposing the users endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.crud import user as crud_user
from backend.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


# ================================================================== #
# User Endpoints                                                     #
# ================================================================== #

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_data: UserCreate
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
    # Check if email already exists
    existing_user = crud_user.get_user_by_email(db=db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    try:
        # crud_user.create_user now returns UserRead schema
        return crud_user.create_user(db=db, user_data=user_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )


@router.get("/", response_model=list[UserRead])
def get_users(
        *,
        db: Annotated[Session, Depends(get_db)],
        skip: int = 0,
        limit: int = 100
) -> list[UserRead]:
    """Get all users.

    Args:
        db: Database session
        skip: Number of users to skip
        limit: Maximum number of users to return

    Returns:
        List of users
    """
    # crud_user.get_all_users now returns list[UserRead]
    return crud_user.get_all_users(db=db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user_by_id(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_id: int
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
    # crud_user.get_user_by_id now returns UserRead or None
    user = crud_user.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_id: int,
        user_data: UserUpdate
) -> UserRead:
    """Update an existing user with partial data (PATCH operation).

    This endpoint allows partial updates of user data. Only the fields provided
    in the request body will be updated. All fields in the UserUpdate schema
    are optional, enabling granular updates.

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

    Example:
        ```json
        {
            "name": "Updated Name",
            "diet_type": "vegetarian"
        }
        ```
        Only the specified fields will be updated, other fields remain unchanged.
    """
    try:
        # crud_user.update_user now returns UserRead or None
        updated_user = crud_user.update_user(db=db, user_id=user_id, user_data=user_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        return updated_user
    except ValueError as exc:
        if "Email is already taken" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc


@router.delete("/{user_id}")
def delete_user(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_id: int
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
            detail=f"User with ID {user_id} not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Additional User Endpoints                                          #
# ================================================================== #

@router.get("/by-email/{email}", response_model=UserRead)
def get_user_by_email(
        *,
        db: Annotated[Session, Depends(get_db)],
        email: str
) -> UserRead:
    """Get user by email address.

    Args:
        db: Database session
        email: Email address to search for

    Returns:
        User data

    Raises:
        HTTPException: 404 if user not found
    """
    user = crud_user.get_user_by_email(db=db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{email}' not found"
        )

    return user
