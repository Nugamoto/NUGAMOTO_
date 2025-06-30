"""Inventory management API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud import inventory as crud_inventory
from app.models.user import User
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    StorageLocationCreate,
    StorageLocationRead,
    StorageLocationUpdate,
)

# Create router
inventory_router = APIRouter()

# Sub-routers for different resource types
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
        current_user: Annotated[User, Depends(get_current_user)],
        kitchen_id: int,
        storage_data: StorageLocationCreate
) -> StorageLocationRead:
    """Create a new storage location for a kitchen.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        kitchen_id: Kitchen ID to create storage location for
        storage_data: Storage location creation data
        
    Returns:
        Created storage location data
        
    Raises:
        HTTPException: 400 if storage location name already exists in kitchen
    """
    try:
        storage_location = crud_inventory.create_storage_location(
            db=db,
            kitchen_id=kitchen_id,
            storage_data=storage_data
        )
        return StorageLocationRead.model_validate(storage_location)
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
        current_user: Annotated[User, Depends(get_current_user)],
        kitchen_id: int
) -> list[StorageLocationRead]:
    """Get all storage locations for a kitchen.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        kitchen_id: Kitchen ID to get storage locations for
        
    Returns:
        List of storage location data
    """
    storage_locations = crud_inventory.get_kitchen_storage_locations(db, kitchen_id)
    return [StorageLocationRead.model_validate(location) for location in storage_locations]


@storage_locations_router.get(
    "/{storage_location_id}",
    response_model=StorageLocationRead,
    summary="Get a storage location by ID",
)
def get_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        storage_location_id: int
) -> StorageLocationRead:
    """Get a storage location by its ID.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        storage_location_id: Storage location ID to fetch
        
    Returns:
        Storage location data
        
    Raises:
        HTTPException: 404 if storage location not found
    """
    storage_location = crud_inventory.get_storage_location_by_id(db, storage_location_id)
    if storage_location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location with ID {storage_location_id} not found"
        )
    return StorageLocationRead.model_validate(storage_location)


@storage_locations_router.put(
    "/{storage_location_id}",
    response_model=StorageLocationRead,
    summary="Update a storage location",
)
def update_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        storage_location_id: int,
        storage_data: StorageLocationUpdate
) -> StorageLocationRead:
    """Update an existing storage location.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        storage_location_id: Storage location ID to update
        storage_data: Updated storage location data
        
    Returns:
        Updated storage location data
        
    Raises:
        HTTPException: 404 if storage location not found
    """
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
    return StorageLocationRead.model_validate(storage_location)


@storage_locations_router.delete(
    "/{storage_location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a storage location",
)
def delete_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        storage_location_id: int
) -> None:
    """Delete a storage location.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        storage_location_id: Storage location ID to delete
        
    Raises:
        HTTPException: 404 if storage location not found
    """
    deleted = crud_inventory.delete_storage_location(db, storage_location_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location with ID {storage_location_id} not found"
        )


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
        current_user: Annotated[User, Depends(get_current_user)],
        kitchen_id: int,
        inventory_data: InventoryItemCreate
) -> InventoryItemRead:
    """Create a new inventory item or update existing one.
    
    If an inventory item for the same food item and storage location already
    exists, the quantities will be combined and other fields updated.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        kitchen_id: Kitchen ID to create inventory item for
        inventory_data: Inventory item creation data
        
    Returns:
        Created or updated inventory item data with computed properties
        
    Raises:
        HTTPException: 400 if food_item_id or storage_location_id don't exist
    """
    try:
        inventory_item = crud_inventory.create_or_update_inventory_item(
            db=db,
            kitchen_id=kitchen_id,
            inventory_data=inventory_data
        )
        return crud_inventory._build_inventory_item_read(inventory_item)
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
        current_user: Annotated[User, Depends(get_current_user)],
        kitchen_id: int
) -> list[InventoryItemRead]:
    """Get all inventory items for a kitchen.
    
    Returns items with related food item and storage location information.
    Quantities are shown in the food item's base unit with computed properties.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        kitchen_id: Kitchen ID to get inventory for
        
    Returns:
        List of inventory item data with computed properties
    """
    return crud_inventory.get_kitchen_inventory(db, kitchen_id)


@inventory_items_router.get(
    "/{inventory_id}",
    response_model=InventoryItemRead,
    summary="Get an inventory item by ID",
)
def get_inventory_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        inventory_id: int
) -> InventoryItemRead:
    """Get an inventory item by its global ID.

    Returns the item with related food item and storage location information.
    Quantity is shown in the food item's base unit with computed properties.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        inventory_id: Inventory item ID to fetch
        
    Returns:
        Inventory item data with computed properties
        
    Raises:
        HTTPException: 404 if inventory item not found
    """
    item = crud_inventory.get_inventory_item_by_id(db, inventory_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found"
        )
    return item


@inventory_items_router.put(
    "/{inventory_id}",
    response_model=InventoryItemRead,
    summary="Update an inventory item",
)
def update_inventory_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        inventory_id: int,
        inventory_data: InventoryItemUpdate
) -> InventoryItemRead:
    """Update an existing inventory item.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        inventory_id: Inventory item ID to update
        inventory_data: Updated inventory item data
        
    Returns:
        Updated inventory item data with computed properties
        
    Raises:
        HTTPException: 404 if inventory item not found
    """
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
    return crud_inventory._build_inventory_item_read(inventory_item)


@inventory_items_router.delete(
    "/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an inventory item",
)
def delete_inventory_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        inventory_id: int
) -> None:
    """Delete an inventory item.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        inventory_id: Inventory item ID to delete
        
    Raises:
        HTTPException: 404 if inventory item not found
    """
    deleted = crud_inventory.delete_inventory_item(db, inventory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found"
        )


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
        current_user: Annotated[User, Depends(get_current_user)],
        kitchen_id: int
) -> list[InventoryItemRead]:
    """Get all inventory items that are below their minimum quantity threshold.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        kitchen_id: Kitchen ID to analyze
        
    Returns:
        List of low-stock inventory items with computed properties
    """
    low_stock_items = crud_inventory.get_low_stock_items(db, kitchen_id)
    return [crud_inventory._build_inventory_item_read(item) for item in low_stock_items]


@inventory_items_router.get(
    "/analysis/expiring",
    response_model=list[InventoryItemRead],
    summary="Get items that are expiring soon",
)
def get_expiring_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        kitchen_id: int,
        threshold_days: int = 7
) -> list[InventoryItemRead]:
    """Get all inventory items that expire within the specified threshold.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        kitchen_id: Kitchen ID to analyze
        threshold_days: Number of days to consider as "expiring soon"
        
    Returns:
        List of expiring inventory items with computed properties
    """
    expiring_items = crud_inventory.get_expiring_items(db, kitchen_id, threshold_days)
    return [crud_inventory._build_inventory_item_read(item) for item in expiring_items]


@inventory_items_router.get(
    "/analysis/expired",
    response_model=list[InventoryItemRead],
    summary="Get items that have already expired",
)
def get_expired_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        current_user: Annotated[User, Depends(get_current_user)],
        kitchen_id: int
) -> list[InventoryItemRead]:
    """Get all inventory items that have already expired.
    
    Args:
        db: Database session
        current_user: Currently authenticated user
        kitchen_id: Kitchen ID to analyze
        
    Returns:
        List of expired inventory items with computed properties
    """
    expired_items = crud_inventory.get_expired_items(db, kitchen_id)
    return [crud_inventory._build_inventory_item_read(item) for item in expired_items]


# ================================================================== #
# Register Sub-Routers                                               #
# ================================================================== #

inventory_router.include_router(storage_locations_router)
inventory_router.include_router(inventory_items_router)