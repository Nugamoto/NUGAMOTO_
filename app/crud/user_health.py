"""CRUD operations for user health profiles v2.0 - Schema Returns."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.models.user_health import UserHealthProfile
from app.schemas.user_health import (
    UserHealthProfileCreate,
    UserHealthProfileRead,
    UserHealthProfileSummary,
    UserHealthProfileUpdate
)


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_user_health_profile_read(profile_orm: UserHealthProfile) -> UserHealthProfileRead:
    """Convert UserHealthProfile ORM to Read schema."""
    return UserHealthProfileRead.model_validate(profile_orm, from_attributes=True)


def build_user_health_profile_summary(profile_orm: UserHealthProfile) -> UserHealthProfileSummary:
    """Convert UserHealthProfile ORM to Summary schema."""
    return UserHealthProfileSummary.model_validate(profile_orm, from_attributes=True)


# ================================================================== #
# User Health Profile CRUD - Schema Returns                         #
# ================================================================== #

def create_user_health_profile(
        db: Session,
        user_id: int,
        profile_data: UserHealthProfileCreate
) -> UserHealthProfileRead:
    """Create new health profile for a user - returns schema.

    Args:
        db: Database session.
        user_id: ID of the user to create profile for.
        profile_data: Validated health profile creation data.

    Returns:
        The newly created health profile schema.

    Raises:
        ValueError: If user_id is invalid or user doesn't exist.
        IntegrityError: If health profile already exists for this user.
    """
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    user = crud_user.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} does not exist")

    existing_profile = get_user_health_profile_orm_by_user_id(db, user_id)
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

    return build_user_health_profile_read(db_profile)


def get_user_health_profile_by_user_id(db: Session, user_id: int) -> UserHealthProfileRead | None:
    """Retrieve health profile by user ID - returns schema.

    Args:
        db: Database session.
        user_id: ID of the user whose health profile is to retrieve.

    Returns:
        UserHealthProfile schema if found, None otherwise.
    """
    profile_orm = get_user_health_profile_orm_by_user_id(db, user_id)

    if not profile_orm:
        return None

    return build_user_health_profile_read(profile_orm)


def get_user_health_profile_by_id(db: Session, profile_id: int) -> UserHealthProfileRead | None:
    """Retrieve health profile by profile ID - returns schema.

    Args:
        db: Database session.
        profile_id: ID of the health profile to retrieve.

    Returns:
        UserHealthProfile schema if found, None otherwise.
    """
    profile_orm = get_user_health_profile_orm_by_id(db, profile_id)

    if not profile_orm:
        return None

    return build_user_health_profile_read(profile_orm)


def get_all_health_profiles(
        db: Session,
        skip: int = 0,
        limit: int = 100
) -> list[UserHealthProfileSummary]:
    """Retrieve all health profiles with pagination - returns schemas.

    Args:
        db: Database session.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List of UserHealthProfile summary schemas, ordered by user_id.
    """
    profiles_list = db.scalars(
        select(UserHealthProfile)
        .offset(skip)
        .limit(limit)
        .order_by(UserHealthProfile.user_id)
    ).all()

    return [build_user_health_profile_summary(profile) for profile in profiles_list]


def update_user_health_profile(
        db: Session,
        user_id: int,
        profile_data: UserHealthProfileUpdate
) -> UserHealthProfileRead | None:
    """Update existing health profile with partial data - returns schema.

    Args:
        db: Database session.
        user_id: ID of the user whose health profile is to update.
        profile_data: Partial health profile data to update (only non-None fields are updated).

    Returns:
        Updated UserHealthProfile schema if found, None otherwise.
    """
    profile_orm = get_user_health_profile_orm_by_user_id(db, user_id)
    if not profile_orm:
        return None

    # Update only the fields that are not None
    update_data = profile_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(profile_orm, field, value)

    profile_orm.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(profile_orm)

    return build_user_health_profile_read(profile_orm)


def search_health_profiles(
        db: Session,
        min_age: int | None = None,
        max_age: int | None = None,
        gender: str | None = None,
        activity_level: str | None = None,
        min_bmi: float | None = None,
        max_bmi: float | None = None
) -> list[UserHealthProfileSummary]:
    """Search health profiles by various criteria - returns schemas.

    Args:
        db: Database session.
        min_age: Minimum age filter.
        max_age: Maximum age filter.
        gender: Gender filter (case-insensitive).
        activity_level: Activity level filter (case-insensitive).
        min_bmi: Minimum BMI filter (calculated dynamically).
        max_bmi: Maximum BMI filter (calculated dynamically).

    Returns:
        List of UserHealthProfile summary schemas matching the criteria.
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
        profiles = filtered_profiles

    return [build_user_health_profile_summary(profile) for profile in profiles]


# ================================================================== #
# ORM Helper Functions (for internal use)                           #
# ================================================================== #

def get_user_health_profile_orm_by_user_id(db: Session, user_id: int) -> UserHealthProfile | None:
    """Get UserHealthProfile ORM object by user ID - for internal use."""
    return db.scalar(
        select(UserHealthProfile).where(UserHealthProfile.user_id == user_id)
    )


def get_user_health_profile_orm_by_id(db: Session, profile_id: int) -> UserHealthProfile | None:
    """Get UserHealthProfile ORM object by profile ID - for internal use."""
    return db.scalar(
        select(UserHealthProfile).where(UserHealthProfile.id == profile_id)
    )
