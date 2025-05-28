"""CRUD helper functions for the *User* model."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate


def get_user(db: Session, user_id: int) -> Optional[User]:
    """Return a user by primary key.

    Args:
        db: Database session.
        user_id: Primary key of the user.

    Returns:
        The matching :class:`~app.models.user.User` or ``None``.
    """
    stmt = select(User).where(User.id == user_id)
    return db.scalar(stmt)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return a user by *unique* e-mail address (case-insensitive).

    Args:
        db: Database session.
        email: Email address to search for.

    Returns:
        The matching user or ``None``.
    """
    stmt = select(User).where(User.email == email.lower())
    return db.scalar(stmt)


def create_user(db: Session, user_in: UserCreate) -> User:
    """Create and persist a new user.

    Args:
        db: Database session.
        user_in: Validated user payload.

    Returns:
        The newly created, *refreshed* user instance.
    """
    new_user = User(
        name=user_in.name,
        email=user_in.email.lower(),
        diet_type=user_in.diet_type,
        allergies=user_in.allergies,
        preferences=user_in.preferences,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user