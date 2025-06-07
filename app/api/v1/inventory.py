"""API endpoints for inventory management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import food as crud_food
from app.crud import inventory as crud_inventory
from app.schemas.food import FoodItemRead
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    KitchenInventorySummary,
    StorageLocationCreate,
    StorageLocationRead,
    StorageLocationUpdate,
    StorageLocationWithInventory
)

# Create separate routers for different resource types
kitchen_router = APIRouter()
storage_router = APIRouter()
inventory_items_router = APIRouter()

# Legacy router for backward compatibility
router = APIRouter()


# ================================================================== #
# Storage Location Endpoints                                         #
# ================================================================== #

@storage_router.post(
    "/kitchens/{kitchen_id}/storage-locations/",
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
    """Create a new storage location for a kitchen.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
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
        return StorageLocationRead.model_validate(storage_location, from_attributes=True)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Storage location '{storage_data.name}' already exists in this kitchen"
        )


@kitchen_router.get(
    "/kitchens/{kitchen_id}/storage-locations/",
    response_model=list[StorageLocationRead],
    summary="Get all storage locations for a kitchen",
)
def get_kitchen_storage_locations(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int
) -> list[StorageLocationRead]:
    """Get all storage locations for a kitchen.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of storage locations
    """
    storage_locations = crud_inventory.get_kitchen_storage_locations(
        db=db,
        kitchen_id=kitchen_id
    )
    return [
        StorageLocationRead.model_validate(storage, from_attributes=True)
        for storage in storage_locations
    ]


@storage_router.get(
    "/storage-locations/{storage_location_id}",
    response_model=StorageLocationRead,
    summary="Get a storage location by ID",
)
def get_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        storage_location_id: int
) -> StorageLocationRead:
    """Get storage location by ID.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to fetch
        
    Returns:
        Storage location data
        
    Raises:
        HTTPException: 404 if storage location not found
    """
    storage_location = crud_inventory.get_storage_location_by_id(
        db=db,
        storage_location_id=storage_location_id
    )
    if not storage_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location with ID {storage_location_id} not found"
        )

    return StorageLocationRead.model_validate(storage_location, from_attributes=True)


@storage_router.patch(
    "/storage-locations/{storage_location_id}",
    response_model=StorageLocationRead,
    summary="Update a storage location",
)
def update_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        storage_location_id: int,
        storage_data: StorageLocationUpdate
) -> StorageLocationRead:
    """Update a storage location.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to update
        storage_data: Updated storage location data
        
    Returns:
        Updated storage location data
        
    Raises:
        HTTPException: 404 if storage location not found
    """
    updated_storage = crud_inventory.update_storage_location(
        db=db,
        storage_location_id=storage_location_id,
        storage_data=storage_data
    )
    if not updated_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location with ID {storage_location_id} not found"
        )

    return StorageLocationRead.model_validate(updated_storage, from_attributes=True)


@storage_router.delete(
    "/storage-locations/{storage_location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a storage location",
)
def delete_storage_location(
        *,
        db: Annotated[Session, Depends(get_db)],
        storage_location_id: int
) -> Response:
    """Delete a storage location.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to delete
        
    Raises:
        HTTPException: 404 if storage location not found
    """
    success = crud_inventory.delete_storage_location(
        db=db,
        storage_location_id=storage_location_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage location with ID {storage_location_id} not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Inventory Item Endpoints                                           #
# ================================================================== #

@inventory_items_router.post(
    "/kitchens/{kitchen_id}/inventory-items/",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an inventory item",
)
def add_inventory_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int,
        inventory_data: InventoryItemCreate
) -> InventoryItemRead:
    """Add an inventory item to a kitchen.
    
    If an item for the same food and storage location already exists,
    quantities will be combined.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        inventory_data: Inventory item creation data
        
    Returns:
        Created or updated inventory item data
        
    Raises:
        HTTPException: 400 if food_item_id or storage_location_id don't exist
    """
    # Validate that food item exists
    food_item = crud_food.get_food_item_by_id(
        db=db,
        food_item_id=inventory_data.food_item_id
    )
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with ID {inventory_data.food_item_id} not found"
        )

    # Validate that storage location exists and belongs to the kitchen
    storage_location = crud_inventory.get_storage_location_by_id(
        db=db,
        storage_location_id=inventory_data.storage_location_id
    )
    if not storage_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Storage location with ID {inventory_data.storage_location_id} not found"
        )

    if storage_location.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Storage location {storage_location.id} does not belong to kitchen {kitchen_id}"
        )

    inventory_item = crud_inventory.create_or_update_inventory_item(
        db=db,
        kitchen_id=kitchen_id,
        inventory_data=inventory_data
    )

    # Manually build the response with computed properties
    return _build_inventory_item_read(inventory_item)


@kitchen_router.get(
    "/kitchens/{kitchen_id}/inventory/",
    response_model=list[InventoryItemRead],
    summary="Get kitchen inventory",
)
def get_kitchen_inventory(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int,
        food_item_id: Annotated[int | None, Query(description="Filter by food item")] = None,
        storage_location_id: Annotated[int | None, Query(description="Filter by storage location")] = None
) -> list[InventoryItemRead]:
    """Get inventory items for a kitchen with optional filtering.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        food_item_id: Optional food item filter
        storage_location_id: Optional storage location filter
        
    Returns:
        List of inventory items with computed properties
    """
    inventory_items = crud_inventory.get_kitchen_inventory(
        db=db,
        kitchen_id=kitchen_id,
        food_item_id=food_item_id,
        storage_location_id=storage_location_id
    )

    return [_build_inventory_item_read(item) for item in inventory_items]


@kitchen_router.get(
    "/kitchens/{kitchen_id}/inventory/summary/",
    response_model=KitchenInventorySummary,
    summary="Get kitchen inventory summary",
)
def get_kitchen_inventory_summary(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int
) -> KitchenInventorySummary:
    """Get a summary of a kitchen's inventory grouped by storage location.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        Kitchen inventory summary with statistics
    """
    grouped_inventory = crud_inventory.get_kitchen_inventory_grouped_by_storage(
        db=db,
        kitchen_id=kitchen_id
    )

    storage_locations = []
    total_items = 0
    low_stock_items = 0
    expired_items = 0
    expires_soon_items = 0

    for storage_location, items in grouped_inventory.items():
        inventory_reads = [_build_inventory_item_read(item) for item in items]

        storage_locations.append(StorageLocationWithInventory(
            **StorageLocationRead.model_validate(
                storage_location,
                from_attributes=True
            ).model_dump(),
            inventory_items=inventory_reads
        ))

        # Update statistics
        total_items += len(items)
        for item in items:
            if item.is_low_stock():
                low_stock_items += 1
            if item.is_expired():
                expired_items += 1
            if item.expires_soon():
                expires_soon_items += 1

    return KitchenInventorySummary(
        kitchen_id=kitchen_id,
        storage_locations=storage_locations,
        total_items=total_items,
        low_stock_items=low_stock_items,
        expired_items=expired_items,
        expires_soon_items=expires_soon_items
    )


@kitchen_router.get(
    "/kitchens/{kitchen_id}/inventory/low-stock/",
    response_model=list[InventoryItemRead],
    summary="Get low stock items",
)
def get_low_stock_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int
) -> list[InventoryItemRead]:
    """Get all inventory items that are below their minimum quantity threshold.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of low stock inventory items
    """
    low_stock_items = crud_inventory.get_low_stock_items(
        db=db,
        kitchen_id=kitchen_id
    )

    return [_build_inventory_item_read(item) for item in low_stock_items]


@kitchen_router.get(
    "/kitchens/{kitchen_id}/inventory/expiring/",
    response_model=list[InventoryItemRead],
    summary="Get expiring items",
)
def get_expiring_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        kitchen_id: int,
        threshold_days: Annotated[int, Query(ge=1, le=365, description="Days until expiration")] = 7
) -> list[InventoryItemRead]:
    """Get all inventory items that expire within the specified threshold.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        threshold_days: Number of days to consider as "expiring soon"
        
    Returns:
        List of expiring inventory items ordered by expiration date
    """
    expiring_items = crud_inventory.get_expiring_items(
        db=db,
        kitchen_id=kitchen_id,
        threshold_days=threshold_days
    )

    return [_build_inventory_item_read(item) for item in expiring_items]


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
    """Get an inventory item by its global ID.

    Returns the item with related food item and storage location information.
    Quantity is shown in the food item's base unit.
    
    Args:
        db: Database session
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

    return _build_inventory_item_read(item)


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
    """Update an inventory item.
    
    Args:
        db: Database session
        inventory_id: Inventory item ID to update
        inventory_data: Updated inventory item data
        
    Returns:
        Updated inventory item data
        
    Raises:
        HTTPException: 404 if inventory item not found, 400 if referenced entities don't exist
    """
    # Validate food_item_id if provided
    if inventory_data.food_item_id is not None:
        food_item = crud_food.get_food_item_by_id(
            db=db,
            food_item_id=inventory_data.food_item_id
        )
        if not food_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Food item with ID {inventory_data.food_item_id} not found"
            )

    # Validate storage_location_id if provided
    if inventory_data.storage_location_id is not None:
        storage_location = crud_inventory.get_storage_location_by_id(
            db=db,
            storage_location_id=inventory_data.storage_location_id
        )
        if not storage_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Storage location with ID {inventory_data.storage_location_id} not found"
            )

    updated_item = crud_inventory.update_inventory_item(
        db=db,
        inventory_item_id=inventory_id,
        inventory_data=inventory_data
    )
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found"
        )

    return _build_inventory_item_read(updated_item)


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
    """Delete an inventory item.
    
    Args:
        db: Database session
        inventory_id: Inventory item ID to delete
        
    Raises:
        HTTPException: 404 if inventory item not found
    """
    success = crud_inventory.delete_inventory_item(
        db=db,
        inventory_item_id=inventory_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory item with ID {inventory_id} not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Helper Functions                                                   #
# ================================================================== #

def _build_inventory_item_read(item) -> InventoryItemRead:
    """Build an InventoryItemRead with computed properties.
    
    Args:
        item: InventoryItem instance with loaded relationships
        
    Returns:
        InventoryItemRead with all computed properties
    """
    # Build FoodItemRead
    food_item_read = FoodItemRead(
        id=item.food_item.id,
        name=item.food_item.name,
        category=item.food_item.category,
        base_unit_id=item.food_item.base_unit_id,
        created_at=item.food_item.created_at,
        last_updated=item.food_item.last_updated,
        base_unit_name=item.food_item.base_unit.name if item.food_item.base_unit else None
    )

    # Build StorageLocationRead
    storage_location_read = StorageLocationRead(
        id=item.storage_location.id,
        kitchen_id=item.storage_location.kitchen_id,
        name=item.storage_location.name
    )

    return InventoryItemRead(
        id=item.id,
        kitchen_id=item.kitchen_id,
        food_item_id=item.food_item_id,
        storage_location_id=item.storage_location_id,
        quantity=item.quantity,
        min_quantity=item.min_quantity,
        expiration_date=item.expiration_date,
        last_updated=item.last_updated,
        food_item=food_item_read,
        storage_location=storage_location_read,
        is_low_stock=item.is_low_stock(),
        is_expired=item.is_expired(),
        expires_soon=item.expires_soon(),
        base_unit_name=item.food_item.base_unit.name if item.food_item.base_unit else None
    )
