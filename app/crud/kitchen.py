"""CRUD helper functions for the *Kitchen* and *UserKitchen* models."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.kitchen import Kitchen, UserKitchen
from app.models.user import User
from app.schemas.kitchen import KitchenCreate, KitchenUpdate, UserKitchenCreate


def create_kitchen(db: Session, kitchen_data: KitchenCreate) -> Kitchen:
    """Create and persist a new kitchen.

    Args:
        db: Database session.
        kitchen_data: Validated kitchen payload.

    Returns:
        The newly created, *refreshed* kitchen instance.
    """
    new_kitchen = Kitchen(name=kitchen_data.name)
    db.add(new_kitchen)
    db.commit()
    db.refresh(new_kitchen)
    return new_kitchen


def get_kitchen_by_id(db: Session, kitchen_id: int) -> Kitchen | None:
    """Return a kitchen by primary key.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        The matching :class:`~app.models.kitchen.Kitchen` or ``None``.
    """
    stmt = select(Kitchen).where(Kitchen.id == kitchen_id)
    return db.scalar(stmt)


def get_kitchen_with_users(db: Session, kitchen_id: int) -> Kitchen | None:
    """Return a kitchen by primary key with all associated users.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        The matching kitchen with users loaded, or ``None``.
    """
    stmt = (
        select(Kitchen)
        .options(selectinload(Kitchen.user_kitchens).selectinload(UserKitchen.user))
        .where(Kitchen.id == kitchen_id)
    )
    return db.scalar(stmt)


def get_all_kitchens(db: Session) -> list[Kitchen]:
    """Return all kitchens from the database.

    Args:
        db: Database session.

    Returns:
        A list of all kitchens in the database.
    """
    stmt = select(Kitchen)
    return list(db.scalars(stmt).all())


def update_kitchen(db: Session, kitchen_id: int, kitchen_data: KitchenUpdate) -> Kitchen:
    """Update an existing kitchen with partial data.

    Args:
        db: Active database session.
        kitchen_id: Primary key of the target kitchen.
        kitchen_data: Validated payload containing partial kitchen data.

    Returns:
        The updated and refreshed kitchen instance.

    Raises:
        ValueError: If the kitchen does not exist.
    """
    kitchen = get_kitchen_by_id(db, kitchen_id)
    if kitchen is None:
        raise ValueError("Kitchen not found.")

    if kitchen_data.name is not None:
        kitchen.name = kitchen_data.name

    db.commit()
    db.refresh(kitchen)
    return kitchen


def delete_kitchen(db: Session, kitchen_id: int) -> None:
    """Remove a kitchen from the database.

    Args:
        db: Active database session.
        kitchen_id: Primary key of the kitchen to delete.

    Raises:
        ValueError: If the kitchen does not exist.
    """
    kitchen = get_kitchen_by_id(db, kitchen_id)
    if kitchen is None:
        raise ValueError("Kitchen not found.")

    db.delete(kitchen)
    db.commit()


def add_user_to_kitchen(
        db: Session, kitchen_id: int, user_kitchen_data: UserKitchenCreate
) -> UserKitchen:
    """Add a user to a kitchen with a specific role.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        user_kitchen_data: Validated payload containing user_id and role.

    Returns:
        The newly created UserKitchen relationship.

    Raises:
        ValueError: If the kitchen or user does not exist, or if the relationship already exists.
    """
    # Check if kitchen exists
    kitchen = get_kitchen_by_id(db, kitchen_id)
    if kitchen is None:
        raise ValueError("Kitchen not found.")

    # Check if user exists
    user_stmt = select(User).where(User.id == user_kitchen_data.user_id)
    user = db.scalar(user_stmt)
    if user is None:
        raise ValueError("User not found.")

    # Check if relationship already exists
    existing_stmt = select(UserKitchen).where(
        UserKitchen.user_id == user_kitchen_data.user_id,
        UserKitchen.kitchen_id == kitchen_id,
    )
    if db.scalar(existing_stmt) is not None:
        raise ValueError("User is already a member of this kitchen.")

    # Create the relationship
    user_kitchen = UserKitchen(
        user_id=user_kitchen_data.user_id,
        kitchen_id=kitchen_id,
        role=user_kitchen_data.role,
    )
    db.add(user_kitchen)
    db.commit()
    db.refresh(user_kitchen)
    return user_kitchen


def remove_user_from_kitchen(db: Session, kitchen_id: int, user_id: int) -> None:
    """Remove a user from a kitchen.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        user_id: Primary key of the user.

    Raises:
        ValueError: If the relationship does not exist.
    """
    stmt = select(UserKitchen).where(
        UserKitchen.user_id == user_id,
        UserKitchen.kitchen_id == kitchen_id,
    )
    user_kitchen = db.scalar(stmt)
    if user_kitchen is None:
        raise ValueError("User is not a member of this kitchen.")

    db.delete(user_kitchen)
    db.commit()


def get_user_kitchens(db: Session, user_id: int) -> list[UserKitchen]:
    """Get all kitchens a user belongs to.

    Args:
        db: Database session.
        user_id: Primary key of the user.

    Returns:
        A list of UserKitchen relationships for the user.
    """
    stmt = (
        select(UserKitchen)
        .options(selectinload(UserKitchen.kitchen))
        .where(UserKitchen.user_id == user_id)
    )
    return list(db.scalars(stmt).all())
