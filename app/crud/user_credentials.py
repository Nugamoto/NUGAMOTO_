"""CRUD operations for user credentials and authentication data v2.0 - Schema Returns."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.models.user_credentials import UserCredentials
from app.schemas.user_credentials import (
    UserCredentialsCreate,
    UserCredentialsRead,
    UserCredentialsSummary,
    UserCredentialsUpdate
)


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_user_credentials_read(credentials_orm: UserCredentials) -> UserCredentialsRead:
    """Convert UserCredentials ORM to Read schema."""
    return UserCredentialsRead.model_validate(credentials_orm, from_attributes=True)


def build_user_credentials_summary(credentials_orm: UserCredentials) -> UserCredentialsSummary:
    """Convert UserCredentials ORM to Summary schema."""
    return UserCredentialsSummary.model_validate(credentials_orm, from_attributes=True)


# ================================================================== #
# User Credentials CRUD - Schema Returns                            #
# ================================================================== #

def create_user_credentials(
        db: Session,
        user_id: int,
        credentials_data: UserCredentialsCreate
) -> UserCredentialsRead:
    """Create new user credentials - returns schema.

    Args:
        db: Database session.
        user_id: ID of the user to create credentials for.
        credentials_data: Validated credential creation data.

    Returns:
        The newly created user credentials schema.

    Raises:
        ValueError: If user_id is invalid or user doesn't exist.
        IntegrityError: If credentials already exist for this user.
    """
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    user = crud_user.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} does not exist")

    existing_credentials = get_user_credentials_orm_by_user_id(db, user_id)
    if existing_credentials:
        raise ValueError("Credentials already exist for this user")

    db_credentials = UserCredentials(
        user_id=user_id,
        password_hash=credentials_data.password_hash,
        first_name=credentials_data.first_name,
        last_name=credentials_data.last_name,
        address=credentials_data.address,
        city=credentials_data.city,
        postal_code=credentials_data.postal_code,
        country=credentials_data.country,
        phone=credentials_data.phone,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        updated_at=datetime.datetime.now(datetime.timezone.utc)
    )

    db.add(db_credentials)
    db.commit()
    db.refresh(db_credentials)

    return build_user_credentials_read(db_credentials)


def get_user_credentials_by_user_id(db: Session, user_id: int) -> UserCredentialsRead | None:
    """Retrieve user credentials by user ID - returns schema.

    Args:
        db: Database session.
        user_id: ID of the user whose credentials are to retrieve.

    Returns:
        UserCredentials schema if found, None otherwise.
    """
    credentials_orm = get_user_credentials_orm_by_user_id(db, user_id)

    if not credentials_orm:
        return None

    return build_user_credentials_read(credentials_orm)


def get_all_user_credentials(
        db: Session,
        skip: int = 0,
        limit: int = 100
) -> list[UserCredentialsSummary]:
    """Retrieve all user credentials with pagination - returns schemas.

    Args:
        db: Database session.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List of UserCredentials summary schemas, ordered by user_id.
    """
    credentials_list = db.scalars(
        select(UserCredentials)
        .offset(skip)
        .limit(limit)
        .order_by(UserCredentials.user_id)
    ).all()

    return [build_user_credentials_summary(cred) for cred in credentials_list]


def update_user_credentials(
        db: Session,
        user_id: int,
        credentials_data: UserCredentialsUpdate
) -> UserCredentialsRead | None:
    """Update existing user credentials with partial data - returns schema.

    Args:
        db: Database session.
        user_id: ID of the user whose credentials are to update.
        credentials_data: Partial credentials data to update (only non-None fields are updated).

    Returns:
        Updated UserCredentials schema if found, None otherwise.
    """
    credentials_orm = get_user_credentials_orm_by_user_id(db, user_id)
    if not credentials_orm:
        return None

    # Update only the fields that are not None
    update_data = credentials_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(credentials_orm, field, value)

    credentials_orm.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(credentials_orm)

    return build_user_credentials_read(credentials_orm)


def search_user_credentials(
        db: Session,
        first_name_contains: str | None = None,
        last_name_contains: str | None = None,
        city: str | None = None,
        country: str | None = None
) -> list[UserCredentialsSummary]:
    """Search user credentials by various criteria - returns schemas.

    Args:
        db: Database session.
        first_name_contains: Filter by first name containing text (case-insensitive).
        last_name_contains: Filter by last name containing text (case-insensitive).
        city: Filter by exact city match.
        country: Filter by exact country match.

    Returns:
        List of UserCredentials summary schemas matching the criteria.
    """
    stmt = select(UserCredentials)

    if first_name_contains:
        stmt = stmt.where(UserCredentials.first_name.ilike(f"%{first_name_contains.strip()}%"))
    if last_name_contains:
        stmt = stmt.where(UserCredentials.last_name.ilike(f"%{last_name_contains.strip()}%"))
    if city:
        stmt = stmt.where(UserCredentials.city == city.strip())
    if country:
        stmt = stmt.where(UserCredentials.country == country.strip())

    credentials_list = db.scalars(stmt).all()
    return [build_user_credentials_summary(cred) for cred in credentials_list]


# ================================================================== #
# ORM Helper Functions (for internal use)                           #
# ================================================================== #

def get_user_credentials_orm_by_user_id(db: Session, user_id: int) -> UserCredentials | None:
    """Get UserCredentials ORM object by user ID - for internal use."""
    return db.scalar(
        select(UserCredentials).where(UserCredentials.user_id == user_id)
    )