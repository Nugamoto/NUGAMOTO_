"""API endpoints for user health profiles."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import user_health as crud_user_health
from app.schemas.user_health import (
    UserHealthProfileCreate,
    UserHealthProfileRead,
    UserHealthProfileUpdate
)

router = APIRouter(prefix="/users", tags=["User Health Profiles"])


@router.get(
    "/{user_id}/health-profile",
    response_model=UserHealthProfileRead,
    summary="Get user's health profile"
)
def get_user_health_profile(
    user_id: int,
    db: Annotated[Session, Depends(get_db)]
) -> UserHealthProfileRead:
    """Retrieve a user's health profile.

    Args:
        user_id: The unique identifier of the user.
        db: Database session dependency.

    Returns:
        The user's health profile with all available data.

    Raises:
        HTTPException: 404 if no health profile found for the user.

    Example:
        GET /users/123/health-profile
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    profile = crud_user_health.get_user_health_profile_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health profile found for user {user_id}"
        )

    return UserHealthProfileRead.model_validate(profile, from_attributes=True)


@router.post(
    "/{user_id}/health-profile",
    response_model=UserHealthProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new health profile"
)
def create_health_profile(
    user_id: int,
    profile_data: UserHealthProfileCreate,
    db: Annotated[Session, Depends(get_db)]
) -> UserHealthProfileRead:
    """Create a new health profile for a user.

    Args:
        user_id: The unique identifier of the user.
        profile_data: Health profile data to create.
        db: Database session dependency.

    Returns:
        The created health profile.

    Raises:
        HTTPException: 
            - 400 if user_id is invalid or profile already exists.
            - 404 if user_id doesn't exist in the system.

    Example:
        POST /users/123/health-profile
        ```json
        {
            "age": 30,
            "gender": "male",
            "height_cm": 180,
            "weight_kg": 75.0,
            "activity_level": "moderately active",
            "goal": "maintain health"
        }
        ```
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    # Check if profile already exists
    existing_profile = crud_user_health.get_user_health_profile_by_user_id(db, user_id)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Health profile already exists for user {user_id}. Use PATCH to update."
        )

    try:
        profile = crud_user_health.create_user_health_profile(
            db, user_id, profile_data
        )
        return UserHealthProfileRead.model_validate(profile, from_attributes=True)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except IntegrityError:
        db.rollback()
        # This could happen if user_id doesn't exist (foreign key constraint)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )


@router.patch(
    "/{user_id}/health-profile",
    response_model=UserHealthProfileRead,
    summary="Update user's health profile"
)
def update_health_profile(
    user_id: int,
    profile_data: UserHealthProfileUpdate,
    db: Annotated[Session, Depends(get_db)]
) -> UserHealthProfileRead:
    """Update an existing health profile with partial data.

    Args:
        user_id: The unique identifier of the user.
        profile_data: Health profile data to update (only provided fields are updated).
        db: Database session dependency.

    Returns:
        The updated health profile.

    Raises:
        HTTPException: 
            - 400 if user_id is invalid.
            - 404 if no health profile found for the user.

    Example:
        PATCH /users/123/health-profile
        ```json
        {
            "weight_kg": 72.5,
            "activity_level": "very active"
        }
        ```

    Note:
        All fields are optional. Only provided fields will be updated.
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    try:
        profile = crud_user_health.update_user_health_profile(
            db, user_id, profile_data
        )
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No health profile found for user {user_id}"
            )

        return UserHealthProfileRead.model_validate(profile, from_attributes=True)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{user_id}/health-profile",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user's health profile"
)
def delete_user_health_profile(
    user_id: int,
    db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete a user's health profile.

    Args:
        user_id: The unique identifier of the user.
        db: Database session dependency.

    Returns:
        Empty response with 204 status code.

    Raises:
        HTTPException: 
            - 400 if user_id is invalid.
            - 404 if no health profile found for the user.

    Example:
        DELETE /users/123/health-profile
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    success = crud_user_health.delete_user_health_profile(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health profile found for user {user_id}"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)