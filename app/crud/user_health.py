"""CRUD operations for user health profiles."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.models.user_health import UserHealthProfile
from app.schemas.user_health import UserHealthProfileCreate, UserHealthProfileUpdate


def create_user_health_profile(
        db: Session,
        user_id: int,
        profile_data: UserHealthProfileCreate
) -> UserHealthProfile:
    """Create new health profile for a user.

    Args:
        db: Database session.
        user_id: ID of the user to create profile for.
        profile_data: Validated health profile creation data.

    Returns:
        The newly created and persisted health profile instance.

    Raises:
        ValueError: If user_id is invalid or user doesn't exist.
        IntegrityError: If health profile already exists for this user.
    """
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    user = crud_user.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} does not exist")

    existing_profile = get_user_health_profile_by_user_id(db, user_id)
    if existing_profile:
        raise ValueError("Health profile already exists for this user")

    db_profile = UserHealthProfile(
        user_id=user_id,
        age=profile_data.age,
        gender=profile_data.gender,
        height_cm=profile_data.height_cm,
        weight_kg=profile_data.weight_kg,
        activity_level=profile_data.activity_level,
        health_conditions=profile_data.health_conditions,
        goal=profile_data.goal,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )

    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)

    return db_profile


def get_user_health_profile_by_user_id(db: Session, user_id: int) -> UserHealthProfile | None:
    """Retrieve health profile by user ID.

    Args:
        db: Database session.
        user_id: ID of the user whose health profile is to retrieve.

    Returns:
        UserHealthProfile instance if found, None otherwise.
    """
    return db.scalar(
        select(UserHealthProfile).where(UserHealthProfile.user_id == user_id)
    )


def get_user_health_profile_by_id(db: Session, profile_id: int) -> UserHealthProfile | None:
    """Retrieve health profile by profile ID.

    Args:
        db: Database session.
        profile_id: ID of the health profile to retrieve.

    Returns:
        UserHealthProfile instance if found, None otherwise.
    """
    return db.scalar(
        select(UserHealthProfile).where(UserHealthProfile.id == profile_id)
    )


def get_all_health_profiles(
        db: Session,
        skip: int = 0,
        limit: int = 100
) -> list[UserHealthProfile]:
    """Retrieve all health profiles with pagination.

    Args:
        db: Database session.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List of UserHealthProfile instances, ordered by user_id.
    """
    return list(db.scalars(
        select(UserHealthProfile)
        .offset(skip)
        .limit(limit)
        .order_by(UserHealthProfile.user_id)
    ).all())


def update_user_health_profile(
        db: Session,
        user_id: int,
        profile_data: UserHealthProfileUpdate
) -> UserHealthProfile | None:
    """Update existing health profile with partial data.

    Args:
        db: Database session.
        user_id: ID of the user whose health profile is to update.
        profile_data: Partial health profile data to update (only non-None fields are updated).

    Returns:
        Updated UserHealthProfile instance if found, None otherwise.
    """
    profile = get_user_health_profile_by_user_id(db, user_id)
    if not profile:
        return None

    # Update only the fields that are not None
    update_data = profile_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(profile)

    return profile


def search_health_profiles(
        db: Session,
        min_age: int | None = None,
        max_age: int | None = None,
        gender: str | None = None,
        activity_level: str | None = None,
        min_bmi: float | None = None,
        max_bmi: float | None = None
) -> list[UserHealthProfile]:
    """Search health profiles by various criteria.

    Args:
        db: Database session.
        min_age: Minimum age filter.
        max_age: Maximum age filter.
        gender: Gender filter (case-insensitive).
        activity_level: Activity level filter (case-insensitive).
        min_bmi: Minimum BMI filter (calculated dynamically).
        max_bmi: Maximum BMI filter (calculated dynamically).

    Returns:
        List of UserHealthProfile instances matching the criteria.
    """
    stmt = select(UserHealthProfile)

    if min_age is not None:
        stmt = stmt.where(UserHealthProfile.age >= min_age)
    if max_age is not None:
        stmt = stmt.where(UserHealthProfile.age <= max_age)
    if gender is not None:
        stmt = stmt.where(UserHealthProfile.gender == gender.lower())
    if activity_level is not None:
        stmt = stmt.where(UserHealthProfile.activity_level == activity_level.lower())

    profiles = list(db.scalars(stmt).all())

    # Filter by BMI if specified (requires calculation)
    if min_bmi is not None or max_bmi is not None:
        filtered_profiles = []
        for profile in profiles:
            bmi = profile.bmi
            if bmi is not None:
                if min_bmi is not None and bmi < min_bmi:
                    continue
                if max_bmi is not None and bmi > max_bmi:
                    continue
            filtered_profiles.append(profile)
        return filtered_profiles

    return profiles
