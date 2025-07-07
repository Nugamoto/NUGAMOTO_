"""CRUD operations for user system."""

from __future__ import annotations

from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_user_read(user_orm: User) -> UserRead:
    """Convert User ORM to Read schema.
    
    Args:
        user_orm: User ORM object
        
    Returns:
        UserRead schema
    """
    # Use Pydantic's from_attributes to handle the conversion properly
    return UserRead.model_validate(user_orm, from_attributes=True)


# ================================================================== #
# User CRUD Operations - Schema Returns                             #
# ================================================================== #

def create_user(db: Session, user_data: UserCreate) -> UserRead:
    """Create and persist a new user - returns schema.

    Args:
        db: Database session
        user_data: Validated user payload

    Returns:
        Created user schema

    Raises:
        IntegrityError: If email already exists
    """
    db_user = User(
        name=user_data.name,
        email=str(user_data.email).lower(),
        diet_type=user_data.diet_type,
        allergies=user_data.allergies,
        preferences=user_data.preferences,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return build_user_read(db_user)


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> list[UserRead]:
    """Return all users from the database - returns schemas.

    Args:
        db: Database session
        skip: Number of users to skip
        limit: Maximum number of users to return

    Returns:
        List of user schemas
    """
    user_orms = db.scalars(
        select(User)
        .order_by(User.name)
        .offset(skip)
        .limit(limit)
    ).all()

    return [build_user_read(user) for user in user_orms]


def get_user_by_id(db: Session, user_id: int) -> UserRead | None:
    """Return a user by primary key - returns schema.

    Args:
        db: Database session
        user_id: Primary key of the user

    Returns:
        User schema or None if not found
    """
    user_orm = db.scalar(
        select(User).where(User.id == user_id)
    )

    if not user_orm:
        return None

    return build_user_read(user_orm)


def get_user_by_email(db: Session, email: str | EmailStr) -> UserRead | None:
    """Return a user by unique e-mail address - returns schema.

    Args:
        db: Database session
        email: Email address to search for

    Returns:
        User schema or None if not found
    """
    normalized = str(email).lower()
    user_orm = db.scalar(
        select(User).where(User.email == normalized)
    )

    if not user_orm:
        return None

    return build_user_read(user_orm)


def update_user(db: Session, user_id: int, user_data: UserUpdate) -> UserRead | None:
    """Update an existing user with partial data - returns schema.

    This function implements proper PATCH semantics by:
    - Only updating fields that are explicitly provided (not None)
    - Preserving existing values for fields not included in the request
    - Validating email uniqueness only when email is being changed
    - Using explicit field-by-field updates instead of bulk assignment

    Args:
        db: Active database session
        user_id: Primary key of the target user
        user_data: Validated payload containing partial user data

    Returns:
        Updated user schema or None if not found

    Raises:
        ValueError: If the e-mail is already taken by another user
    """
    # Get ORM object first
    user_orm = db.scalar(
        select(User).where(User.id == user_id)
    )

    if not user_orm:
        return None

    # Only update fields that were provided (exclude_unset=True)
    update_data = user_data.model_dump(exclude_unset=True)

    # Special handling for email uniqueness check
    if 'email' in update_data:
        normalized_email = str(update_data['email']).lower()
        existing_user_orm = db.scalar(
            select(User).where(User.email == normalized_email)
        )
        if existing_user_orm and existing_user_orm.id != user_id:
            raise ValueError("Email is already taken.")
        update_data['email'] = normalized_email

    # Apply updates
    for field, value in update_data.items():
        setattr(user_orm, field, value)

    db.commit()
    db.refresh(user_orm)

    return build_user_read(user_orm)


def delete_user(db: Session, user_id: int) -> bool:
    """Remove a user from the database.

    Args:
        db: Active database session
        user_id: Primary key of the user to delete

    Returns:
        True if deleted, False if not found
    """
    user_orm = db.scalar(
        select(User).where(User.id == user_id)
    )

    if not user_orm:
        return False

    db.delete(user_orm)
    db.commit()

    return True


# ================================================================== #
# ORM-based Functions (for internal use when ORM objects needed)     #
# ================================================================== #

def get_user_orm_by_id(db: Session, user_id: int) -> User | None:
    """Return a user ORM object by primary key.
    
    This function is for internal use when other CRUD operations need
    the actual ORM object (e.g., for relationships).

    Args:
        db: Database session
        user_id: Primary key of the user

    Returns:
        User ORM object or None if not found
    """
    return db.scalar(
        select(User).where(User.id == user_id)
    )


def get_user_orm_by_email(db: Session, email: str | EmailStr) -> User | None:
    """Return a user ORM object by email.
    
    This function is for internal use when other CRUD operations need
    the actual ORM object (e.g., for relationships).

    Args:
        db: Database session
        email: Email address to search for

    Returns:
        User ORM object or None if not found
    """
    normalized = str(email).lower()
    return db.scalar(
        select(User).where(User.email == normalized)
    )
