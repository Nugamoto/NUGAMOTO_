"""CRUD helper functions for the *User* model."""

from __future__ import annotations

from pydantic import EmailStr
from sqlalchemy import select, Sequence
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create and persist a new user.

    Args:
        db: Database session.
        user_data: Validated user payload.

    Returns:
        The newly created, *refreshed* user instance.
    """
    new_user = User(
        name=user_data.name,
        email=str(user_data.email).lower(),
        diet_type=user_data.diet_type,
        allergies=user_data.allergies,
        preferences=user_data.preferences,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def get_all_users(db: Session) -> Sequence[User]:
    """Return all users from the database.

    Args:
        db: Database session.

    Returns:
        A sequence of all users in the database.
    """
    stmt = select(User)
    return db.scalars(stmt).all()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return a user by primary key.

    Args:
        db: Database session.
        user_id: Primary key of the user.

    Returns:
        The matching : class:`~app.models.user.User` or ``None``.
    """
    stmt = select(User).where(User.id == user_id)
    return db.scalar(stmt)


def get_user_by_email(db: Session, email: str | EmailStr) -> User | None:
    """Return a user by *unique* e-mail address (case-insensitive).

    Args:
        db: Database session.
        email: Email address to search for.

    Returns:
        The matching user or ``None``.
    """
    normalized = email.lower()
    stmt = select(User).where(User.email == normalized)
    return db.scalar(stmt)




def update_user(db: Session, user_id: int, user_data: UserUpdate) -> User | None:
    """Update an existing user with partial data (PATCH-conform).

    This function implements proper PATCH semantics by:
    - Only updating fields that are explicitly provided (not None)
    - Preserving existing values for fields not included in the request
    - Validating email uniqueness only when email is being changed
    - Using explicit field-by-field updates instead of bulk assignment

    Args:
        db: Active database session.
        user_id: Primary key of the target user.
        user_data: Validated payload containing partial user data.

    Returns:
        The updated and refreshed user instance.

    Raises:
        ValueError: If the user does not exist or the e-mail is already taken.
    """
    user = get_user_by_id(db, user_id)
    if user is None:
        return None

    # Nur Felder aktualisieren, die übergeben wurden
    if user_data.name is not None:
        user.name = user_data.name

    if user_data.email is not None:
        normalized_email = str(user_data.email).lower()
        existing_user = get_user_by_email(db, normalized_email)
        if existing_user and existing_user.id != user_id:
            raise ValueError("Email is already taken.")
        user.email = normalized_email

    if user_data.diet_type is not None:
        user.diet_type = user_data.diet_type

    if user_data.allergies is not None:
        user.allergies = user_data.allergies

    if user_data.preferences is not None:
        user.preferences = user_data.preferences

    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> None:
    """Remove a user from the database.

    Args:
        db: Active database session.
        user_id: Primary key of the user to delete.

    Raises:
        ValueError: If the user does not exist.
    """
    user = get_user_by_id(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    db.delete(user)
    db.commit()
