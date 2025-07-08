
"""FastAPI router exposing the kitchens endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import kitchen as crud_kitchen
from app.schemas.kitchen import (
    KitchenCreate,
    KitchenRead,
    KitchenUpdate,
    KitchenWithUsers,
    UserKitchenCreate,
    UserKitchenRead,
    UserKitchenUpdate,
)

# ================================================================== #
# Sub-routers for better organization                               #
# ================================================================== #

kitchens_router = APIRouter(tags=["Kitchens"])
users_router = APIRouter(prefix="/users", tags=["Kitchen Users"])


# ================================================================== #
# Kitchen Management CRUD                                           #
# ================================================================== #

@kitchens_router.post(
    "/",
    response_model=KitchenRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new kitchen",
)
def create_kitchen(
        kitchen_data: KitchenCreate,
        db: Session = Depends(get_db)
) -> KitchenRead:
    """Create a new kitchen.

    Args:
        kitchen_data: Validated kitchen payload.
        db: Injected database session.

    Returns:
        The newly created kitchen.
    """
    return crud_kitchen.create_kitchen(db, kitchen_data)


@kitchens_router.get(
    "/",
    response_model=list[KitchenRead],
    status_code=status.HTTP_200_OK,
    summary="Get all kitchens",
)
def get_all_kitchens(db: Session = Depends(get_db)) -> list[KitchenRead]:
    """Retrieve all kitchens from the database.

    Args:
        db: Injected database session.

    Returns:
        A list of all kitchens.
    """
    return crud_kitchen.get_all_kitchens(db)


@kitchens_router.get(
    "/{kitchen_id}",
    response_model=KitchenWithUsers,
    status_code=status.HTTP_200_OK,
    summary="Get kitchen details with users",
)
def get_kitchen(kitchen_id: int, db: Session = Depends(get_db)) -> KitchenWithUsers:
    """Retrieve a kitchen by ID including all associated users.

    Args:
        kitchen_id: Primary key of the kitchen.
        db: Injected database session.

    Returns:
        The requested kitchen with all associated users.

    Raises:
        HTTPException: 404 if the kitchen does not exist.
    """
    kitchen = crud_kitchen.get_kitchen_with_users(db, kitchen_id)
    if kitchen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen not found"
        )

    return kitchen


@kitchens_router.patch(
    "/{kitchen_id}",
    response_model=KitchenRead,
    status_code=status.HTTP_200_OK,
    summary="Update an existing kitchen",
)
def update_kitchen(
        kitchen_id: int,
        kitchen_data: KitchenUpdate,
        db: Session = Depends(get_db),
) -> KitchenRead:
    """Partially update an existing kitchen.

    This endpoint allows partial updates of kitchen data. Only the fields provided
    in the request body will be updated. All fields in the KitchenUpdate schema
    are optional, enabling granular updates.

    Args:
        kitchen_id: Primary key of the kitchen to update.
        kitchen_data: Partial kitchen data containing only fields to be updated.
        db: Injected database session.

    Returns:
        The updated kitchen with all current field values.

    Raises:
        HTTPException: 404 if the kitchen does not exist.

    Example:
        ```json
        {
            "name": "Updated Kitchen Name"
        }
        ```
        Only the specified fields will be updated, other fields remain unchanged.
    """
    updated_kitchen = crud_kitchen.update_kitchen(db, kitchen_id, kitchen_data)
    if updated_kitchen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen not found"
        )

    return updated_kitchen


@kitchens_router.delete(
    "/{kitchen_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a kitchen",
)
def delete_kitchen(
        kitchen_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a kitchen by primary key.

    This will also automatically delete all user-kitchen relationships
    due to the cascade="all, delete-orphan" configuration.

    Args:
        kitchen_id: ID of the kitchen to delete.
        db: Injected database session.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the kitchen does not exist.
    """
    deleted = crud_kitchen.delete_kitchen(db, kitchen_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Kitchen Users & Memberships                                       #
# ================================================================== #

@users_router.post(
    "/{kitchen_id}/",
    response_model=UserKitchenRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add user to kitchen",
)
def add_user_to_kitchen(
        kitchen_id: int,
        user_kitchen_data: UserKitchenCreate,
        db: Session = Depends(get_db),
) -> UserKitchenRead:
    """Add a user to a kitchen with a specific role.

    Args:
        kitchen_id: Primary key of the kitchen.
        user_kitchen_data: User ID and role information.
        db: Injected database session.

    Returns:
        The created user-kitchen relationship.

    Raises:
        HTTPException:
            * 404 – if the kitchen or user does not exist.
            * 400 – if the user is already a member of this kitchen.
    """
    try:
        return crud_kitchen.add_user_to_kitchen(db, kitchen_id, user_kitchen_data)
    except ValueError as exc:
        error_msg = str(exc)
        if "Kitchen not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kitchen not found"
            ) from exc
        elif "User not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            ) from exc
        elif "already a member" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this kitchen"
            ) from exc
        # Re-raise unexpected errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add user to kitchen: {error_msg}"
        ) from exc


@users_router.get(
    "/{kitchen_id}/{user_id}",
    response_model=UserKitchenRead,
    status_code=status.HTTP_200_OK,
    summary="Get user's role in kitchen",
)
def get_user_role_in_kitchen(
        kitchen_id: int,
        user_id: int,
        db: Session = Depends(get_db)
) -> UserKitchenRead:
    """Get a user's role in a specific kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        user_id: Primary key of the user.
        db: Injected database session.

    Returns:
        The user-kitchen relationship with role information.

    Raises:
        HTTPException: 404 if the relationship does not exist.
    """
    user_kitchen = crud_kitchen.get_user_kitchen_relationship(db, kitchen_id, user_id)
    if user_kitchen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this kitchen"
        )

    return user_kitchen


@users_router.patch(
    "/{kitchen_id}/{user_id}/role",
    response_model=UserKitchenRead,
    status_code=status.HTTP_200_OK,
    summary="Update user role in kitchen",
)
def update_user_role_in_kitchen(
        kitchen_id: int,
        user_id: int,
        role_data: UserKitchenUpdate,
        db: Session = Depends(get_db),
) -> UserKitchenRead:
    """Update a user's role in a kitchen.

    This endpoint allows updating the role of a user within a specific kitchen.
    Only the role field will be updated as specified in the request body.

    Args:
        kitchen_id: Primary key of the kitchen.
        user_id: Primary key of the user.
        role_data: New role information to be updated.
        db: Injected database session.

    Returns:
        The updated user-kitchen relationship with the new role.

    Raises:
        HTTPException: 404 if the user-kitchen relationship does not exist.

    Example:
        ```json
        {
            "role": "ADMIN"
        }
        ```
        Only the role will be updated, preserving other relationship data.
    """
    user_kitchen = crud_kitchen.update_user_role_in_kitchen(
        db, kitchen_id, user_id, role_data
    )
    if user_kitchen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this kitchen"
        )

    return user_kitchen


@users_router.delete(
    "/{kitchen_id}/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from kitchen",
)
def remove_user_from_kitchen(
        kitchen_id: int,
        user_id: int,
        db: Session = Depends(get_db)
) -> Response:
    """Remove a user from a kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        user_id: Primary key of the user.
        db: Injected database session.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the user-kitchen relationship does not exist.
    """
    removed = crud_kitchen.remove_user_from_kitchen(db, kitchen_id, user_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this kitchen"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get(
    "/{user_id}/kitchens",
    response_model=list[UserKitchenRead],
    status_code=status.HTTP_200_OK,
    summary="Get all kitchens for a user",
)
def get_user_kitchens(
        user_id: int,
        db: Session = Depends(get_db)
) -> list[UserKitchenRead]:
    """Get all kitchens a user belongs to.

    Args:
        user_id: Primary key of the user.
        db: Injected database session.

    Returns:
        List of user-kitchen relationships for the user.
    """
    return crud_kitchen.get_user_kitchens(db, user_id)


# ================================================================== #
# Main Router Assembly                                               #
# ================================================================== #

router = APIRouter(prefix="/kitchens")

# Include all sub-routers
router.include_router(kitchens_router)
router.include_router(users_router)
