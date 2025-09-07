"""CRUD operations for user health profiles v2.0 - Schema Returns."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.crud import user as crud_user
from backend.models.user_health import UserHealthProfile
from backend.schemas.user_health import (
    UserHealthProfileCreate,
    UserHealthProfileRead,
    UserHealthProfileSummary,
    UserHealthProfileUpdate
)


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_user_health_profile_read(profile_orm: UserHealthProfile) -> UserHealthProfileRead:
    """Convert a UserHealthProfile ORM object to a read DTO.

    Normalisiert leere Strings (Alt-Daten) zu None, bevor das Pydantic-Read-
    Schema validiert wird. So schlagen strikte Validatoren (min_length etc.)
    nicht beim Lesen fehl.

    Args:
        profile_orm: Vollständig geladenes ORM-Objekt.

    Returns:
        UserHealthProfileRead: Validiere, normalisierte Leserepräsentation.
    """
    data = {
        "id": profile_orm.id,
        "user_id": profile_orm.user_id,
        "age": profile_orm.age,
        "gender": _none_if_empty(profile_orm.gender),
        "height_cm": profile_orm.height_cm,
        "weight_kg": profile_orm.weight_kg,
        "activity_level": _none_if_empty(profile_orm.activity_level),
        "health_conditions": _none_if_empty(profile_orm.health_conditions),
        "goal": _none_if_empty(profile_orm.goal),
        "created_at": profile_orm.created_at,
        "updated_at": profile_orm.updated_at,
        "bmi": profile_orm.bmi,
        "is_complete": profile_orm.is_complete,
    }
    return UserHealthProfileRead.model_validate(data)


def build_user_health_profile_summary(profile_orm: UserHealthProfile) -> UserHealthProfileSummary:
    """Convert a UserHealthProfile ORM object to a summary DTO.

    Normalisiert leere Strings (Alt-Daten) zu None, bevor das Pydantic-Summary-
    Schema validiert wird.

    Args:
        profile_orm: Vollständig geladenes ORM-Objekt.

    Returns:
        UserHealthProfileSummary: Validiere, normalisierte Zusammenfassung.
    """
    data = {
        "id": profile_orm.id,
        "user_id": profile_orm.user_id,
        "age": profile_orm.age,
        "gender": _none_if_empty(profile_orm.gender),
        "bmi": profile_orm.bmi,
        "activity_level": _none_if_empty(profile_orm.activity_level),
        "goal": _none_if_empty(profile_orm.goal),
        "is_complete": profile_orm.is_complete,
        "updated_at": profile_orm.updated_at,
    }
    return UserHealthProfileSummary.model_validate(data)


# ================================================================== #
# User Health Profile CRUD - Schema Returns                         #
# ================================================================== #

def create_user_health_profile(
        db: Session,
        user_id: int,
        profile_data: UserHealthProfileCreate
) -> UserHealthProfileRead:
    """Create a new health profile for a user and return the read schema.

    Normalizes empty strings to None for text fields before persisting.

    Args:
        db: Database session.
        user_id: Target user ID.
        profile_data: Validated health profile payload.

    Returns:
        UserHealthProfileRead: Created profile.

    Raises:
        ValueError: If user_id is invalid or user doesn't exist, or a profile already exists.
    """
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    user = crud_user.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} does not exist")

    existing_profile = get_user_health_profile_orm_by_user_id(db, user_id)
    if existing_profile:
        raise ValueError("Health profile already exists for this user")

    # Normalize possibly empty strings
    gender = _none_if_empty(profile_data.gender)
    activity_level = _none_if_empty(profile_data.activity_level)
    health_conditions = _none_if_empty(profile_data.health_conditions)
    goal = _none_if_empty(profile_data.goal)

    db_profile = UserHealthProfile(
        user_id=user_id,
        age=profile_data.age,
        gender=gender,
        height_cm=profile_data.height_cm,
        weight_kg=profile_data.weight_kg,
        activity_level=activity_level,
        health_conditions=health_conditions,
        goal=goal,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc),
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
    """Update an existing health profile with partial data and return the read schema.

    Only updates provided fields (PATCH semantics). Empty strings will be
    normalized to None for text fields to keep data consistent.

    Args:
        db: Database session.
        user_id: ID of the user whose profile is updated.
        profile_data: Partial update payload (unset fields are ignored).

    Returns:
        UserHealthProfileRead if found and updated, otherwise None.
    """
    profile_orm = get_user_health_profile_orm_by_user_id(db, user_id)
    if not profile_orm:
        return None

    update_data = profile_data.model_dump(exclude_unset=True)

    # Normalize possibly empty strings for text fields
    for field in ("gender", "activity_level", "health_conditions", "goal"):
        if field in update_data:
            update_data[field] = _none_if_empty(update_data[field])

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


# ================================================================== #
#  Helper Functions                                                  #
# ================================================================== #


def _none_if_empty(value: str | None) -> str | None:
    """Convert empty/whitespace strings to None.

    Args:
        value: Optional string value.

    Returns:
        None if the value is empty or whitespace, otherwise the trimmed value.
    """
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None
