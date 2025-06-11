"""API endpoints for user credentials management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import user_credentials as crud_user_credentials
from app.schemas.user_credentials import (
    UserCredentialsCreate,
    UserCredentialsRead,
    UserCredentialsSummary,
    UserCredentialsUpdate
)

router = APIRouter(prefix="/users", tags=["User Credentials"])


@router.post(
    "/{user_id}/credentials",
    response_model=UserCredentialsRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create user credentials"
)
def create_user_credentials(
        user_id: int,
        credentials_data: UserCredentialsCreate,
        db: Annotated[Session, Depends(get_db)]
) -> UserCredentialsRead:
    """Create new credentials for a user.

    Args:
        user_id: The unique identifier of the user.
        credentials_data: Credentials data to create.
        db: Database session dependency.

    Returns:
        The created credentials with all properties.

    Raises:
        HTTPException:
            - 400 if user_id is invalid.
            - 404 if user doesn't exist.
            - 409 if credentials already exist for this user.

    Example:
        ```json
        {
            "password_hash": "hashed_password_here",
            "first_name": "John",
            "last_name": "Doe",
            "city": "New York",
            "country": "USA",
            "phone": "+1-555-0123"
        }
        ```
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    try:
        credentials = crud_user_credentials.create_user_credentials(
            db=db,
            user_id=user_id,
            credentials_data=credentials_data
        )
        return UserCredentialsRead.model_validate(credentials, from_attributes=True)
    except ValueError as e:
        if "does not exist" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )
        elif "already exist" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Credentials already exist for user {user_id}. Use PATCH to update."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Credentials already exist for this user"
        )


@router.get(
    "/{user_id}/credentials",
    response_model=UserCredentialsRead,
    summary="Get user credentials"
)
def get_user_credentials(
        user_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> UserCredentialsRead:
    """Retrieve a user's credentials and personal information.

    Args:
        user_id: The unique identifier of the user.
        db: Database session dependency.

    Returns:
        The user's credentials with all personal data.

    Raises:
        HTTPException:
            - 400 if user_id is invalid.
            - 404 if no credentials found for the user.

    Example:
        GET /users/123/credentials
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    credentials = crud_user_credentials.get_user_credentials_by_user_id(db, user_id)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials found for user {user_id}"
        )

    return UserCredentialsRead.model_validate(credentials, from_attributes=True)


@router.patch(
    "/{user_id}/credentials",
    response_model=UserCredentialsRead,
    summary="Update user credentials"
)
def update_user_credentials(
        user_id: int,
        credentials_data: UserCredentialsUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> UserCredentialsRead:
    """Update existing user credentials with partial data.

    Args:
        user_id: The unique identifier of the user.
        credentials_data: Credentials data to update (only provided fields are updated).
        db: Database session dependency.

    Returns:
        The updated credentials with all properties.

    Raises:
        HTTPException:
            - 400 if user_id is invalid.
            - 404 if no credentials found for the user.

    Example:
        ```json
        {
            "first_name": "Jane",
            "city": "Los Angeles",
            "phone": "+1-555-0124"
        }
        ```

    Note:
        All fields are optional. Only provided fields will be updated.
    """
    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    updated_credentials = crud_user_credentials.update_user_credentials(
        db=db,
        user_id=user_id,
        credentials_data=credentials_data
    )

    if not updated_credentials:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials found for user {user_id}"
        )

    return UserCredentialsRead.model_validate(updated_credentials, from_attributes=True)


@router.get(
    "/credentials/summary",
    response_model=list[UserCredentialsSummary],
    summary="Get all user credentials summary"
)
def get_all_user_credentials_summary(
        db: Annotated[Session, Depends(get_db)],
        skip: int = 0,
        limit: int = 100
) -> list[UserCredentialsSummary]:
    """Retrieve a summary of all user credentials with pagination.

    Args:
        db: Database session dependency.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List of user credentials summaries.

    Example:
        GET /users/credentials/summary?skip=0&limit=50
    """
    credentials_list = crud_user_credentials.get_all_user_credentials(
        db=db,
        skip=skip,
        limit=limit
    )

    return [
        UserCredentialsSummary.model_validate(credentials, from_attributes=True)
        for credentials in credentials_list
    ]