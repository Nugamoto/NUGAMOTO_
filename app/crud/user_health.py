"""CRUD operations for user health profiles."""

from __future__ import annotations

import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user_health import UserHealthProfile
from app.schemas.user_health import UserHealthProfileCreate, UserHealthProfileUpdate


def get_user_health_profile_by_user_id(
        db: Session,
        user_id: int
) -> UserHealthProfile | None:
    """Retrieve a user's health profile by user ID.

    Args:
        db: Database session.
        user_id: ID of the user whose health profile to retrieve.

    Returns:
        UserHealthProfile instance if found, None otherwise.

    Example:
        >>> profile = get_user_health_profile_by_user_id(db, user_id=123)
        >>> if profile:
        ...     print(f"User {profile.user_id} is {profile.age} years old")
    """
    return db.query(UserHealthProfile).filter(
        UserHealthProfile.user_id == user_id
    ).first()


def create_user_health_profile(
        db: Session,
        user_id: int,
        profile_data: UserHealthProfileCreate
) -> UserHealthProfile:
    """Create a new health profile for a user.

    Args:
        db: Database session.
        user_id: ID of the user.
        profile_data: Health profile data to create.

    Returns:
        The created UserHealthProfile instance.

    Raises:
        ValueError: If user_id is invalid.
        IntegrityError: If a profile already exists for this user.

    Example:
        >>> from app.schemas.user_health import UserHealthProfileCreate
        >>> data = UserHealthProfileCreate(age=30, weight_kg=70.5)
        >>> profile = create_user_health_profile(db, 123, data)
        >>> print(f"Profile created: {profile.last_updated}")
    """
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    # Create new profile
    profile_dict = profile_data.model_dump(exclude_unset=True)
    profile_dict['user_id'] = user_id
    profile_dict['last_updated'] = datetime.datetime.now(datetime.timezone.utc)

    new_profile = UserHealthProfile(**profile_dict)
    db.add(new_profile)

    try:
        db.commit()
        db.refresh(new_profile)
        return new_profile
    except IntegrityError:
        db.rollback()
        raise


def update_user_health_profile(
        db: Session,
        user_id: int,
        profile_data: UserHealthProfileUpdate
) -> UserHealthProfile | None:
    """Update an existing health profile.

    Args:
        db: Database session.
        user_id: ID of the user.
        profile_data: Health profile data to update with.

    Returns:
        The updated UserHealthProfile instance, or None if not found.

    Raises:
        ValueError: If user_id is invalid.

    Example:
        >>> from app.schemas.user_health import UserHealthProfileUpdate
        >>> data = UserHealthProfileUpdate(age=31, weight_kg=72.0)
        >>> profile = update_user_health_profile(db, 123, data)
        >>> if profile:
        ...     print(f"Profile updated: {profile.last_updated}")
    """
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    # Get existing profile
    existing_profile = get_user_health_profile_by_user_id(db, user_id)
    if not existing_profile:
        return None

    # Update existing profile
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_profile, field, value)

    # Update timestamp
    existing_profile.last_updated = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(existing_profile)
    return existing_profile


def delete_user_health_profile(db: Session, user_id: int) -> bool:
    """Delete a user's health profile.

    Args:
        db: Database session.
        user_id: ID of the user whose health profile to delete.

    Returns:
        True if profile was deleted, False if no profile was found.

    Example:
        >>> success = delete_user_health_profile(db, user_id=123)
        >>> if success:
        ...     print("Health profile deleted successfully")
        ... else:
        ...     print("No health profile found for user")
    """
    profile = get_user_health_profile_by_user_id(db, user_id)
    if not profile:
        return False

    db.delete(profile)
    db.commit()
    return True


def get_all_health_profiles(db: Session, skip: int = 0, limit: int = 100) -> list[type[UserHealthProfile]]:
    """Retrieve all health profiles with pagination.

    Args:
        db: Database session.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List of UserHealthProfile instances.

    Example:
        >>> profiles = get_all_health_profiles(db, skip=0, limit=50)
        >>> print(f"Found {len(profiles)} health profiles")
    """
    return db.query(UserHealthProfile).offset(skip).limit(limit).all()


def get_profiles_by_criteria(
        db: Session,
        min_age: int | None = None,
        max_age: int | None = None,
        gender: str | None = None,
        activity_level: str | None = None
) -> list[type[UserHealthProfile]]:
    """Get health profiles matching specific criteria.

    Args:
        db: Database session.
        min_age: Minimum age filter.
        max_age: Maximum age filter.
        gender: Gender filter.
        activity_level: Activity level filter.

    Returns:
        List of UserHealthProfile instances matching the criteria.

    Example:
        >>> profiles = get_profiles_by_criteria(
        ...     db, min_age=25, max_age=35, gender="female"
        ... )
        >>> print(f"Found {len(profiles)} female profiles aged 25-35")
    """
    query = db.query(UserHealthProfile)

    if min_age is not None:
        query = query.filter(UserHealthProfile.age >= min_age)
    if max_age is not None:
        query = query.filter(UserHealthProfile.age <= max_age)
    if gender is not None:
        query = query.filter(UserHealthProfile.gender == gender.lower())
    if activity_level is not None:
        query = query.filter(UserHealthProfile.activity_level == activity_level.lower())

    return query.all()
