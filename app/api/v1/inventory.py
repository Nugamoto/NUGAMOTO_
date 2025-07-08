"""Inventory management API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import inventory as crud_inventory
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    StorageLocationCreate,
    StorageLocationRead,
    StorageLocationUpdate,
)

# ================================================================== #
# Sub-routers for better organization                               #
# ================================================================== #

storage_locations_router = APIRouter(prefix="/storage-locations", tags=["storage-locations"])
inventory_items_router = APIRouter(prefix="/items", tags=["inventory-items"])


# ================================================================== #
# Storage Location Endpoints                                         #
# ================================================================== #

@storage_locations_router.post(
    "/",
    response_model=StorageLocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new storage location",
)
def create_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int,
        storage_data: StorageLocationCreate
) -> StorageLocationRead:
    """Create a new storage location for a kitchen."""
    try:
        return crud_inventory.create_storage_location(
            db=db,
            kitchen_id=kitchen_id,
            storage_data=storage_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create storage location: {str(e)}"
        )


@storage_locations_router.get(
    "/",
    response_model=list[StorageLocationRead],
    summary="Get all storage locations for a kitchen",
)
def get_kitchen_storage_locations(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int
) -> list[StorageLocationRead]:
    """Get all storage locations for a kitchen."""
    return crud_inventory.get_kitchen_storage_locations(db, kitchen_id)


@storage_locations_router.get(
    "/{storage_location_id}",
    response_model=StorageLocationRead,
    summary="Get a storage location by ID",
)
def get_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        storage_location_id: int
) -> StorageLocationRead:
    """Get a storage location by its ID."""
    storage_location = crud_inventory.get_storage_location_by_id(db, storage_location_id)
    if storage_location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location with ID {storage_location_id} not found"
        )
    return storage_location


@storage_locations_router.put(
    "/{storage_location_id}",
    response_model=StorageLocationRead,
    summary="Update a storage location",
)
def update_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        storage_location_id: int,
        storage_data: StorageLocationUpdate
) -> StorageLocationRead:
    """Update an existing storage location."""
    storage_location = crud_inventory.update_storage_location(
        db=db,
        storage_location_id=storage_location_id,
        storage_data=storage_data
    )
    if storage_location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location with ID {storage_location_id} not found"
        )
    return storage_location


@storage_locations_router.delete(
    "/{storage_location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a storage location",
)
def delete_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        storage_location_id: int
) -> Response:
    """Delete a storage location."""
    deleted = crud_inventory.delete_storage_location(db, storage_location_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location with ID {storage_location_id} not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Inventory Item Endpoints                                           #
# ================================================================== #

@inventory_items_router.post(
    "/",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update an inventory item",
)
def create_or_update_inventory_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int,
        inventory_data: InventoryItemCreate
) -> InventoryItemRead:
    """Create a new inventory item or update existing one."""
    try:
        return crud_inventory.create_or_update_inventory_item(
            db=db,
            kitchen_id=kitchen_id,
            inventory_data=inventory_data
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@inventory_items_router.get(
    "/",
    response_model=list[InventoryItemRead],
    summary="Get all inventory items for a kitchen",
)
def get_kitchen_inventory(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int
) -> list[InventoryItemRead]:
    """Get all inventory items for a kitchen."""
    return crud_inventory.get_kitchen_inventory(db, kitchen_id)


@inventory_items_router.get(
    "/{inventory_id}",
    response_model=InventoryItemRead,
    summary="Get an inventory item by ID",
)
def get_inventory_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        inventory_id: int
) -> InventoryItemRead:
    """Get an inventory item by its global ID."""
    item = crud_inventory.get_inventory_item_by_id(db, inventory_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found"
        )
    return item


@inventory_items_router.patch(
    "/{inventory_id}",
    response_model=InventoryItemRead,
    summary="Update an inventory item",
)
def update_inventory_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        inventory_id: int,
        inventory_data: InventoryItemUpdate
) -> InventoryItemRead:
    """Update an existing inventory item."""
    inventory_item = crud_inventory.update_inventory_item(
        db=db,
        inventory_item_id=inventory_id,
        inventory_data=inventory_data
    )
    if inventory_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found"
        )
    return inventory_item


@inventory_items_router.delete(
    "/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an inventory item",
)
def delete_inventory_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        inventory_id: int
) -> Response:
    """Delete an inventory item."""
    deleted = crud_inventory.delete_inventory_item(db, inventory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Inventory Analysis Endpoints                                       #
# ================================================================== #

@inventory_items_router.get(
    "/analysis/low-stock",
    response_model=list[InventoryItemRead],
    summary="Get items that are low in stock",
)
def get_low_stock_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int
) -> list[InventoryItemRead]:
    """Get all inventory items that are below their minimum quantity threshold."""
    return crud_inventory.get_low_stock_items(db, kitchen_id)


@inventory_items_router.get(
    "/analysis/expiring",
    response_model=list[InventoryItemRead],
    summary="Get items that are expiring soon",
)
def get_expiring_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int,
        threshold_days: int = 7
) -> list[InventoryItemRead]:
    """Get all inventory items that expire within the specified threshold."""
    return crud_inventory.get_expiring_items(db, kitchen_id, threshold_days)


@inventory_items_router.get(
    "/analysis/expired",
    response_model=list[InventoryItemRead],
    summary="Get items that have already expired",
)
def get_expired_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int
) -> list[InventoryItemRead]:
    """Get all inventory items that have already expired."""
    return crud_inventory.get_expired_items(db, kitchen_id)


# ================================================================== #
# Main Router Assembly                                               #
# ================================================================== #

router = APIRouter()

# Include all sub-routers
router.include_router(storage_locations_router)
router.include_router(inventory_items_router)
