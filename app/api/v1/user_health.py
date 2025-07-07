
"""API endpoints for user health profiles management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import user_health as crud_user_health
from app.schemas.user_health import (
    UserHealthProfileCreate,
    UserHealthProfileRead,
    UserHealthProfileSummary,
    UserHealthProfileUpdate
)

router = APIRouter(prefix="/users", tags=["User Health Profiles"])


@router.post(
    "/{user_id}/health-profile",
    response_model=UserHealthProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create user health profile"
)
def create_health_profile(
    user_id: int,
    profile_data: UserHealthProfileCreate,
    db: Annotated[Session, Depends(get_db)]
) -> UserHealthProfileRead:
    """Create new health profile for a user.

    Args:
        user_id: The unique identifier of the user.
        profile_data: Health profile data to create.
        db: Database session dependency.

    Returns:
        The created health profile with all properties.

    Raises:
        HTTPException:
            - 400 if user_id is invalid.
            - 404 if user doesn't exist.
            - 409 if health profile already exists for this user.

    Example:
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

    try:
        return crud_user_health.create_user_health_profile(
            db=db,
            user_id=user_id,
            profile_data=profile_data
        )
    except ValueError as e:
        if "does not exist" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        elif "already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Health profile already exists for user {user_id}. Use PATCH to update."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Health profile already exists for this user"
        )


@router.get(
    "/{user_id}/health-profile",
    response_model=UserHealthProfileRead,
    summary="Get user health profile"
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
        The user's health profile with all available data and calculated properties.

    Raises:
        HTTPException:
            - 400 if user_id is invalid.
            - 404 if no health profile found for the user.

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

    return profile


@router.patch(
    "/{user_id}/health-profile",
    response_model=UserHealthProfileRead,
    summary="Update user health profile"
)
def update_health_profile(
    user_id: int,
        profile_data: UserHealthProfileUpdate,
    db: Annotated[Session, Depends(get_db)]
) -> UserHealthProfileRead:
    """Update existing health profile with partial data.

    Args:
        user_id: The unique identifier of the user.
        profile_data: Health profile data to update (only provided fields are updated).
        db: Database session dependency.

    Returns:
        The updated health profile with all properties.

    Raises:
        HTTPException:
            - 400 if user_id is invalid.
            - 404 if no health profile found for the user.

    Example:
        ```json
        {
            "weight_kg": 72.5,
            "activity_level": "very active",
            "goal": "lose weight"
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

    updated_profile = crud_user_health.update_user_health_profile(
        db=db,
        user_id=user_id,
        profile_data=profile_data
    )

    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health profile found for user {user_id}"
        )

    return updated_profile


@router.get(
    "/health-profiles/summary",
    response_model=list[UserHealthProfileSummary],
    summary="Get all health profiles summary"
)
def get_all_health_profiles_summary(
        db: Annotated[Session, Depends(get_db)],
        skip: int = 0,
        limit: int = 100
) -> list[UserHealthProfileSummary]:
    """Retrieve a summary of all health profiles with pagination.

    Args:
        db: Database session dependency.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List of health profile summaries.

    Example:
        GET /users/health-profiles/summary?skip=0&limit=50
    """
    return crud_user_health.get_all_health_profiles(
        db=db,
        skip=skip,
        limit=limit
    )


@router.get(
    "/health-profiles/search",
    response_model=list[UserHealthProfileSummary],
    summary="Search health profiles by criteria"
)
def search_health_profiles(
        db: Annotated[Session, Depends(get_db)],
        min_age: int | None = None,
        max_age: int | None = None,
        gender: str | None = None,
        activity_level: str | None = None,
        min_bmi: float | None = None,
        max_bmi: float | None = None
) -> list[UserHealthProfileSummary]:
    """Search health profiles by various criteria.

    Args:
        db: Database session dependency.
        min_age: Minimum age filter.
        max_age: Maximum age filter.
        gender: Gender filter.
        activity_level: Activity level filter.
        min_bmi: Minimum BMI filter.
        max_bmi: Maximum BMI filter.

    Returns:
        List of health profile summaries matching the criteria.

    Example:
        GET /users/health-profiles/search?min_age=25&max_age=35&gender=female&activity_level=very%20active
    """
    return crud_user_health.search_health_profiles(
        db=db,
        min_age=min_age,
        max_age=max_age,
        gender=gender,
        activity_level=activity_level,
        min_bmi=min_bmi,
        max_bmi=max_bmi
    )
