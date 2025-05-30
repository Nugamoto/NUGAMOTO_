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