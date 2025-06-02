"""CRUD helper functions for the *User* model."""

from __future__ import annotations

from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate


def get_user(db: Session, user_id: int) -> User | None:
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


def update_user(db: Session, user_id: int, user_data: UserCreate) -> User:
    """Update an existing user.

    Args:
        db: Active database session.
        user_id: Primary key of the target user.
        user_data: Validated payload containing the *complete* user data.

    Returns:
        The updated and refreshed user instance.

    Raises:
        ValueError: If the user does not exist or the e-mail is already taken.
    """
    user = get_user(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    # Check for a duplicate e-mail if it is being modified.
    new_email = str(user_data.email).lower()
    if user.email != new_email and get_user_by_email(db, new_email):
        raise ValueError("Email already registered.")

    # Apply incoming changes.
    user.name = user_data.name
    user.email = new_email
    user.diet_type = user_data.diet_type
    user.allergies = user_data.allergies
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
    user = get_user(db, user_id)
    if user is None:
        raise ValueError("User not found.")

    db.delete(user)
    db.commit()
