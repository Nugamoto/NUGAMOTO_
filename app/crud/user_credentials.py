"""CRUD operations for user credentials and authentication data."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.models.user_credentials import UserCredentials
from app.schemas.user_credentials import UserCredentialsCreate, UserCredentialsUpdate


def create_user_credentials(
        db: Session,
        user_id: int,
        credentials_data: UserCredentialsCreate
) -> UserCredentials:
    """Create new user credentials.

    Args:
        db: Database session.
        user_id: ID of the user to create credentials for.
        credentials_data: Validated credentials creation data.

    Returns:
        The newly created and persisted user credentials instance.

    Raises:
        ValueError: If user_id is invalid or user doesn't exist.
        IntegrityError: If credentials already exist for this user.
    """
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer")

    user = crud_user.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} does not exist")

    existing_credentials = get_user_credentials_by_user_id(db, user_id)
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

    return db_credentials


def get_user_credentials_by_user_id(db: Session, user_id: int) -> UserCredentials | None:
    """Retrieve user credentials by user ID.

    Args:
        db: Database session.
        user_id: ID of the user whose credentials to retrieve.

    Returns:
        UserCredentials instance if found, None otherwise.
    """
    return db.scalar(
        select(UserCredentials).where(UserCredentials.user_id == user_id)
    )


def get_all_user_credentials(
        db: Session,
        skip: int = 0,
        limit: int = 100
) -> list[UserCredentials]:
    """Retrieve all user credentials with pagination.

    Args:
        db: Database session.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List of UserCredentials instances, ordered by user_id.
    """
    return list(db.scalars(
        select(UserCredentials)
        .offset(skip)
        .limit(limit)
        .order_by(UserCredentials.user_id)
    ).all())


def update_user_credentials(
        db: Session,
        user_id: int,
        credentials_data: UserCredentialsUpdate
) -> UserCredentials | None:
    """Update existing user credentials with partial data.

    Args:
        db: Database session.
        user_id: ID of the user whose credentials to update.
        credentials_data: Partial credentials data to update (only non-None fields are updated).

    Returns:
        Updated UserCredentials instance if found, None otherwise.
    """
    credentials = get_user_credentials_by_user_id(db, user_id)
    if not credentials:
        return None

    # Update only the fields that are not None
    update_data = credentials_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(credentials, field, value)

    credentials.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(credentials)

    return credentials




def search_user_credentials(
        db: Session,
        first_name_contains: str | None = None,
        last_name_contains: str | None = None,
        city: str | None = None,
        country: str | None = None
) -> list[UserCredentials]:
    """Search user credentials by various criteria.

    Args:
        db: Database session.
        first_name_contains: Filter by first name containing text (case-insensitive).
        last_name_contains: Filter by last name containing text (case-insensitive).
        city: Filter by exact city match.
        country: Filter by exact country match.

    Returns:
        List of UserCredentials instances matching the criteria.
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

    return list(db.scalars(stmt).all())