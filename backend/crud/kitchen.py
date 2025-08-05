
"""CRUD helper functions for the *Kitchen* and *UserKitchen* models."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models.kitchen import Kitchen, UserKitchen
from backend.models.user import User
from backend.schemas.kitchen import (
    KitchenCreate, KitchenRead, KitchenUpdate, KitchenWithUsers,
    UserKitchenCreate, UserKitchenRead, UserKitchenUpdate
)


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_kitchen_read(kitchen_orm: Kitchen) -> KitchenRead:
    """Convert Kitchen ORM to Read schema.

    Args:
        kitchen_orm: Kitchen ORM object

    Returns:
        KitchenRead schema
    """
    return KitchenRead.model_validate(kitchen_orm, from_attributes=True)


def build_kitchen_with_users(kitchen_orm: Kitchen) -> KitchenWithUsers:
    """Convert Kitchen ORM with users to KitchenWithUsers schema.

    Args:
        kitchen_orm: Kitchen ORM object with loaded user_kitchens relationship

    Returns:
        KitchenWithUsers schema
    """
    return KitchenWithUsers.model_validate(kitchen_orm, from_attributes=True)


def build_user_kitchen_read(user_kitchen_orm: UserKitchen) -> UserKitchenRead:
    """Convert UserKitchen ORM to Read schema.

    Args:
        user_kitchen_orm: UserKitchen ORM object with loaded relationships

    Returns:
        UserKitchenRead schema
    """
    return UserKitchenRead.model_validate(user_kitchen_orm, from_attributes=True)


# ================================================================== #
# Kitchen CRUD Operations - Schema Returns                          #
# ================================================================== #

def create_kitchen(db: Session, kitchen_data: KitchenCreate) -> KitchenRead:
    """Create and persist a new kitchen - returns schema.

    Args:
        db: Database session.
        kitchen_data: Validated kitchen payload.

    Returns:
        Created kitchen schema.
    """
    new_kitchen = Kitchen(name=kitchen_data.name)
    db.add(new_kitchen)
    db.commit()
    db.refresh(new_kitchen)

    return build_kitchen_read(new_kitchen)


def get_kitchen_by_id(db: Session, kitchen_id: int) -> KitchenRead | None:
    """Return a kitchen by primary key - returns schema.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        Kitchen schema or None if not found.
    """
    kitchen_orm = db.scalar(
        select(Kitchen).where(Kitchen.id == kitchen_id)
    )

    if not kitchen_orm:
        return None

    return build_kitchen_read(kitchen_orm)


def get_kitchen_with_users(db: Session, kitchen_id: int) -> KitchenWithUsers | None:
    """Return a kitchen by primary key with all associated users - returns schema.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        Kitchen with users schema or None if not found.
    """
    kitchen_orm = db.scalar(
        select(Kitchen)
        .options(selectinload(Kitchen.user_kitchens).selectinload(UserKitchen.user))
        .where(Kitchen.id == kitchen_id)
    )

    if not kitchen_orm:
        return None

    return build_kitchen_with_users(kitchen_orm)


def get_all_kitchens(db: Session) -> list[KitchenRead]:
    """Return all kitchens from the database - returns schemas.

    Args:
        db: Database session.

    Returns:
        List of kitchen schemas.
    """
    kitchen_orms = db.scalars(
        select(Kitchen).order_by(Kitchen.name)
    ).all()

    return [build_kitchen_read(kitchen) for kitchen in kitchen_orms]


def update_kitchen(db: Session, kitchen_id: int, kitchen_data: KitchenUpdate) -> KitchenRead | None:
    """Update an existing kitchen with partial data - returns schema.

    Args:
        db: Active database session.
        kitchen_id: Primary key of the target kitchen.
        kitchen_data: Validated payload containing partial kitchen data.

    Returns:
        Updated kitchen schema or None if not found.
    """
    kitchen_orm = db.scalar(
        select(Kitchen).where(Kitchen.id == kitchen_id)
    )

    if not kitchen_orm:
        return None

    # Only update fields that were provided (exclude_unset=True)
    update_data = kitchen_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(kitchen_orm, field, value)

    db.commit()
    db.refresh(kitchen_orm)

    return build_kitchen_read(kitchen_orm)


def delete_kitchen(db: Session, kitchen_id: int) -> bool:
    """Remove a kitchen from the database.

    Args:
        db: Active database session.
        kitchen_id: Primary key of the kitchen to delete.

    Returns:
        True if deleted, False if not found.
    """
    kitchen_orm = db.scalar(
        select(Kitchen).where(Kitchen.id == kitchen_id)
    )

    if not kitchen_orm:
        return False

    db.delete(kitchen_orm)
    db.commit()

    return True


# ================================================================== #
# UserKitchen CRUD Operations - Schema Returns                      #
# ================================================================== #

def add_user_to_kitchen(
    db: Session, kitchen_id: int, user_kitchen_data: UserKitchenCreate
) -> UserKitchenRead:
    """Add a user to a kitchen with a specific role - returns schema.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        user_kitchen_data: Validated payload containing user_id and role.

    Returns:
        Created UserKitchen relationship schema.

    Raises:
        ValueError: If the kitchen or user does not exist, or if the relationship already exists.
    """
    # Check if kitchen exists
    kitchen_orm = db.scalar(
        select(Kitchen).where(Kitchen.id == kitchen_id)
    )
    if not kitchen_orm:
        raise ValueError("Kitchen not found.")

    # Check if user exists
    user_orm = db.scalar(
        select(User).where(User.id == user_kitchen_data.user_id)
    )
    if not user_orm:
        raise ValueError("User not found.")

    # Check if relationship already exists
    existing_orm = db.scalar(
        select(UserKitchen).where(
            UserKitchen.user_id == user_kitchen_data.user_id,
            UserKitchen.kitchen_id == kitchen_id,
        )
    )
    if existing_orm:
        raise ValueError("User is already a member of this kitchen.")

    # Create the relationship
    user_kitchen_orm = UserKitchen(
        user_id=user_kitchen_data.user_id,
        kitchen_id=kitchen_id,
        role=user_kitchen_data.role,
    )
    db.add(user_kitchen_orm)
    db.commit()
    db.refresh(user_kitchen_orm)

    # Load relationships for schema conversion
    user_kitchen_orm = db.scalar(
        select(UserKitchen)
        .options(selectinload(UserKitchen.user))
        .where(
            UserKitchen.user_id == user_kitchen_data.user_id,
            UserKitchen.kitchen_id == kitchen_id,
        )
    )

    return build_user_kitchen_read(user_kitchen_orm)


def update_user_role_in_kitchen(
    db: Session, kitchen_id: int, user_id: int, role_data: UserKitchenUpdate
) -> UserKitchenRead | None:
    """Update a user's role in a kitchen - returns schema.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        user_id: Primary key of the user.
        role_data: Validated payload containing the new role.

    Returns:
        Updated UserKitchen relationship schema or None if not found.
    """
    # Get the existing relationship
    user_kitchen_orm = db.scalar(
        select(UserKitchen)
        .options(selectinload(UserKitchen.user))
        .where(
            UserKitchen.user_id == user_id,
            UserKitchen.kitchen_id == kitchen_id,
        )
    )

    if not user_kitchen_orm:
        return None

    # Update the role
    user_kitchen_orm.role = role_data.role
    db.commit()
    db.refresh(user_kitchen_orm)

    return build_user_kitchen_read(user_kitchen_orm)


def get_user_kitchen_relationship(
    db: Session, kitchen_id: int, user_id: int
) -> UserKitchenRead | None:
    """Get a specific user-kitchen relationship - returns schema.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        user_id: Primary key of the user.

    Returns:
        UserKitchen relationship schema or None if not found.
    """
    user_kitchen_orm = db.scalar(
        select(UserKitchen)
        .options(selectinload(UserKitchen.user))
        .where(
            UserKitchen.user_id == user_id,
            UserKitchen.kitchen_id == kitchen_id,
        )
    )

    if not user_kitchen_orm:
        return None

    return build_user_kitchen_read(user_kitchen_orm)


def remove_user_from_kitchen(db: Session, kitchen_id: int, user_id: int) -> bool:
    """Remove a user from a kitchen.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        user_id: Primary key of the user.

    Returns:
        True if removed, False if relationship not found.
    """
    user_kitchen_orm = db.scalar(
        select(UserKitchen).where(
            UserKitchen.user_id == user_id,
            UserKitchen.kitchen_id == kitchen_id,
        )
    )

    if not user_kitchen_orm:
        return False

    db.delete(user_kitchen_orm)
    db.commit()

    return True


def get_user_kitchens(db: Session, user_id: int) -> list[UserKitchenRead]:
    """Get all kitchens a user belongs to - returns schemas.

    Args:
        db: Database session.
        user_id: Primary key of the user.

    Returns:
        List of UserKitchen relationship schemas for the user.
    """
    user_kitchen_orms = db.scalars(
        select(UserKitchen)
        .options(selectinload(UserKitchen.kitchen))
        .where(UserKitchen.user_id == user_id)
        .order_by(UserKitchen.kitchen_id)
    ).all()

    return [build_user_kitchen_read(uk) for uk in user_kitchen_orms]


# ================================================================== #
# ORM-based Functions (for internal use when ORM objects needed)     #
# ================================================================== #

def get_kitchen_orm_by_id(db: Session, kitchen_id: int) -> Kitchen | None:
    """Return a kitchen ORM object by primary key.

    This function is for internal use when other CRUD operations need
    the actual ORM object (e.g., for relationships).

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        Kitchen ORM object or None if not found.
    """
    return db.scalar(
        select(Kitchen).where(Kitchen.id == kitchen_id)
    )