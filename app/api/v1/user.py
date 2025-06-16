"""FastAPI router exposing the users endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import user as crud_user
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


# --------------------------------------------------------------------- #
# Endpoints                                                             #
# --------------------------------------------------------------------- #

@router.post(
    "/",
    response_model=UserRead,
    status_code=201,
    summary="Create a new user"
)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if crud_user.get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    db_user = crud_user.create_user(db, user_data)
    return UserRead.model_validate(db_user, from_attributes=True)


@router.get("/",
            response_model=list[UserRead],
            status_code=200,
            summary="Get all users"
            )
def read_all_users(db: Session = Depends(get_db)) -> list[UserRead]:
    """Retrieve all users from the database.

    Args:
        db: Injected database session.

    Returns:
        A list of all users.
    """
    users = crud_user.get_all_users(db)
    return [UserRead.model_validate(user, from_attributes=True) for user in users]

@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get a user by ID",
)
def read_user(user_id: int, db: Session = Depends(get_db)) -> UserRead:
    """Retrieve a single user by primary key.

    Args:
        user_id: Primary key of the user.
        db: Injected database session.

    Returns:
        The requested user.

    Raises:
        HTTPException: *404* if the user does not exist.
    """
    user = crud_user.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserRead.model_validate(user, from_attributes=True)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update an existing user",
)
def update_user(
    user_id: int,
        user_data: UserUpdate,
    db: Session = Depends(get_db),
) -> UserRead:
    """Update an existing user with partial data (PATCH operation).

    This endpoint allows partial updates of user data. Only the fields provided
    in the request body will be updated. All fields in the UserUpdate schema
    are optional, enabling granular updates.

    Args:
        user_id: Primary key of the user to update.
        user_data: Partial user data containing only fields to be updated.
        db: Injected database session.

    Returns:
        The updated user with all current field values.

    Raises:
        HTTPException:
            * 404 – if the user does not exist.
            * 400 – if another user already takes the e-mail address.

    Example:
        ```json
        {
            "name": "Updated Name",
            "diet_type": "vegetarian"
        }
        ```
        Only the specified fields will be updated, other fields remain unchanged.
    """
    try:
        updated_user = crud_user.update_user(db, user_id, user_data)
    except ValueError as exc:
        match str(exc):
            case "User not found.":
                raise HTTPException(status_code=404, detail="User not found.") from exc
            case "Email already registered.":
                raise HTTPException(status_code=400, detail="Email already registered.") from exc
        raise

    if updated_user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    return UserRead.model_validate(updated_user, from_attributes=True)

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
)
def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a user by primary key.

    Args:
        user_id: ID of the user to delete.
        db: Injected database session.

    Raises:
        HTTPException: 404 if the user does not exist.
    """
    try:
        crud_user.delete_user(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="User not found.") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
