"""FastAPI router exposing the kitchens endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.core.dependencies import (
    get_db,
    get_current_user_id,
    require_kitchen_role,
    require_kitchen_member,
)
from backend.core.enums import KitchenRole
from backend.crud import kitchen as crud_kitchen
from backend.schemas.kitchen import (
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
        db: Session = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),
) -> KitchenRead:
    """Create a new kitchen and assign the creator as OWNER.

    Args:
        kitchen_data: Validated kitchen payload.
        db: Injected database session.
        current_user_id: ID of the authenticated user (taken from JWT).

    Returns:
        The newly created kitchen.
    """
    kitchen = crud_kitchen.create_kitchen(db, kitchen_data)

    try:
        crud_kitchen.add_user_to_kitchen(
            db=db,
            kitchen_id=kitchen.id,
            user_kitchen_data=UserKitchenCreate(
                user_id=current_user_id,
                role=KitchenRole.OWNER,
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign owner role to the creator.",
        ) from exc

    return kitchen


@kitchens_router.get(
    "/",
    response_model=list[KitchenRead],
    status_code=status.HTTP_200_OK,
    summary="Get kitchens for current user",
)
def get_all_kitchens(
        db: Session = Depends(get_db),
        current_user_id: int = Depends(get_current_user_id),
) -> list[KitchenRead]:
    """Retrieve kitchens the current user is a member of.

    Args:
        db: Injected database session.
        current_user_id: ID of the authenticated user.

    Returns:
        A list of kitchens the user belongs to.
    """
    memberships = crud_kitchen.get_user_kitchens(db, current_user_id)
    return [KitchenRead.model_validate(m.kitchen, from_attributes=True) for m in memberships]


@kitchens_router.get(
    "/{kitchen_id}",
    response_model=KitchenWithUsers,
    status_code=status.HTTP_200_OK,
    summary="Get kitchen details with users",
    dependencies=[Depends(require_kitchen_member())],
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
            detail="Kitchen not found",
        )
    return kitchen


@kitchens_router.patch(
    "/{kitchen_id}",
    response_model=KitchenRead,
    status_code=status.HTTP_200_OK,
    summary="Update an existing kitchen",
    dependencies=[Depends(require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN}))],
)
def update_kitchen(
        kitchen_id: int,
        kitchen_data: KitchenUpdate,
        db: Session = Depends(get_db),
) -> KitchenRead:
    """Partially update an existing kitchen.

    Only the fields provided in the request body will be updated.

    Args:
        kitchen_id: Primary key of the kitchen to update.
        kitchen_data: Partial kitchen data containing only fields to be updated.
        db: Injected database session.

    Returns:
        The updated kitchen with all current field values.

    Raises:
        HTTPException: 404 if the kitchen does not exist.
    """
    updated_kitchen = crud_kitchen.update_kitchen(db, kitchen_id, kitchen_data)
    if updated_kitchen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kitchen not found",
        )
    return updated_kitchen


@kitchens_router.delete(
    "/{kitchen_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a kitchen",
    dependencies=[Depends(require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN}))],
)
def delete_kitchen(
        kitchen_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a kitchen by primary key.

    This will also automatically delete all user-kitchen relationships
    due to the cascade configuration.

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
            detail="Kitchen not found",
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
    dependencies=[Depends(require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN}))],
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
                status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found"
            ) from exc
        if "User not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            ) from exc
        if "already a member" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this kitchen",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add user to kitchen: {error_msg}",
        ) from exc


@users_router.get(
    "/{kitchen_id}/{user_id}",
    response_model=UserKitchenRead,
    status_code=status.HTTP_200_OK,
    summary="Get user's role in kitchen",
    dependencies=[Depends(require_kitchen_member())],
)
def get_user_role_in_kitchen(
        kitchen_id: int,
        user_id: int,
        db: Session = Depends(get_db),
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
            detail="User is not a member of this kitchen",
        )
    return user_kitchen


@users_router.patch(
    "/{kitchen_id}/{user_id}/role",
    response_model=UserKitchenRead,
    status_code=status.HTTP_200_OK,
    summary="Update user role in kitchen",
    dependencies=[Depends(require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN}))],
)
def update_user_role_in_kitchen(
        kitchen_id: int,
        user_id: int,
        role_data: UserKitchenUpdate,
        db: Session = Depends(get_db),
) -> UserKitchenRead:
    """Update a user's role in a kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        user_id: Primary key of the user.
        role_data: New role information to be updated.
        db: Injected database session.

    Returns:
        The updated user-kitchen relationship with the new role.

    Raises:
        HTTPException: 404 if the user-kitchen relationship does not exist.
    """
    user_kitchen = crud_kitchen.update_user_role_in_kitchen(
        db, kitchen_id, user_id, role_data
    )
    if user_kitchen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this kitchen",
        )
    return user_kitchen


@users_router.delete(
    "/{kitchen_id}/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove user from kitchen",
    dependencies=[Depends(require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN}))],
)
def remove_user_from_kitchen(
        kitchen_id: int,
        user_id: int,
        db: Session = Depends(get_db),
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
            detail="User is not a member of this kitchen",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get(
    "/{user_id}/kitchens",
    response_model=list[UserKitchenRead],
    status_code=status.HTTP_200_OK,
    summary="Get all kitchens for a user",
    dependencies=[Depends(get_current_user_id)],
)
def get_user_kitchens(
        user_id: int,
        db: Session = Depends(get_db),
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