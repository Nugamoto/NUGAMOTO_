"""FastAPI router exposing inventory endpoints with hybrid architecture."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import inventory as crud_inventory
from app.schemas.inventory import (
    FoodItemCreate,
    FoodItemRead,
    FoodItemUpdate,
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    KitchenInventorySummary,
    StorageLocationCreate,
    StorageLocationRead,
    StorageLocationUpdate,
)

# ================================================================== #
# Router Architecture: Kitchen-scoped + Global                      #
# ================================================================== #

# 🏠 Kitchen-scoped router for Storage & Inventory
kitchen_router = APIRouter(prefix="/kitchens", tags=["Inventory - Kitchen"])

# 🌍 Global router for Food Items
food_items_router = APIRouter(prefix="/food-items", tags=["Food Items"])

# 📦 Global router for direct Inventory Item operations
inventory_items_router = APIRouter(prefix="/inventory-items", tags=["Inventory Items"])

# 📍 Global router for direct Storage operations
storage_router = APIRouter(prefix="/storage-locations", tags=["Storage Locations"])


# ================================================================== #
# KITCHEN-SCOPED: Storage & Inventory Operations                    #
# ================================================================== #

@kitchen_router.post(
    "/{kitchen_id}/storage",
    response_model=StorageLocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new storage location for a kitchen",
)
def create_storage_location(
        kitchen_id: int,
        storage_data: StorageLocationCreate,
        db: Session = Depends(get_db),
) -> StorageLocationRead:
    """Create a new storage location for a kitchen."""
    try:
        db_storage = crud_inventory.create_storage_location(db, kitchen_id, storage_data)
    except ValueError as exc:
        if "Kitchen not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StorageLocationRead.model_validate(db_storage, from_attributes=True)


@kitchen_router.get(
    "/{kitchen_id}/storage",
    response_model=list[StorageLocationRead],
    status_code=status.HTTP_200_OK,
    summary="Get all storage locations for a kitchen",
)
def get_kitchen_storage_locations(
        kitchen_id: int,
        db: Session = Depends(get_db)
) -> list[StorageLocationRead]:
    """Retrieve all storage locations for a kitchen."""
    storage_locations = crud_inventory.get_kitchen_storage_locations(db, kitchen_id)
    return [
        StorageLocationRead.model_validate(storage, from_attributes=True)
        for storage in storage_locations
    ]


@kitchen_router.post(
    "/{kitchen_id}/inventory",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an inventory item to a kitchen",
)
def add_inventory_item(
        kitchen_id: int,
        inventory_data: InventoryItemCreate,
        db: Session = Depends(get_db),
) -> InventoryItemRead:
    """Add a new inventory item or update existing quantity."""
    try:
        db_inventory = crud_inventory.create_or_update_inventory_item(
            db, kitchen_id, inventory_data
        )
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Refresh to get computed properties
    inventory_item = crud_inventory.get_inventory_item_by_id(db, db_inventory.id)
    return InventoryItemRead.model_validate(inventory_item, from_attributes=True)


@kitchen_router.get(
    "/{kitchen_id}/inventory",
    response_model=KitchenInventorySummary,
    status_code=status.HTTP_200_OK,
    summary="Get complete kitchen inventory",
)
def get_kitchen_inventory(
        kitchen_id: int,
        db: Session = Depends(get_db)
) -> KitchenInventorySummary:
    """Retrieve complete kitchen inventory grouped by storage location."""
    inventory_summary = crud_inventory.get_kitchen_inventory_grouped_by_storage(
        db, kitchen_id
    )
    return inventory_summary


@kitchen_router.get(
    "/{kitchen_id}/inventory/low-stock",
    response_model=list[InventoryItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get low stock items for a kitchen",
)
def get_low_stock_items(
        kitchen_id: int,
        db: Session = Depends(get_db)
) -> list[InventoryItemRead]:
    """Retrieve all inventory items that are below their minimum quantity."""
    low_stock_items = crud_inventory.get_low_stock_items(db, kitchen_id)
    return [
        InventoryItemRead.model_validate(item, from_attributes=True)
        for item in low_stock_items
    ]


@kitchen_router.get(
    "/{kitchen_id}/inventory/expiring",
    response_model=list[InventoryItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get expiring items for a kitchen",
)
def get_expiring_items(
        kitchen_id: int,
        days: int = 3,
        db: Session = Depends(get_db)
) -> list[InventoryItemRead]:
    """Retrieve all inventory items that expire within the specified number of days."""
    expiring_items = crud_inventory.get_expiring_items(db, kitchen_id, days)
    return [
        InventoryItemRead.model_validate(item, from_attributes=True)
        for item in expiring_items
    ]


# ================================================================== #
# GLOBAL: Food Item Operations                                       #
# ================================================================== #

@food_items_router.post(
    "/",
    response_model=FoodItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new food item",
)
def create_food_item(
        food_item_data: FoodItemCreate,
        db: Session = Depends(get_db)
) -> FoodItemRead:
    """Create a new global food item."""
    try:
        db_food_item = crud_inventory.create_food_item(db, food_item_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FoodItemRead.model_validate(db_food_item, from_attributes=True)


@food_items_router.get(
    "/",
    response_model=list[FoodItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get all food items",
)
def get_all_food_items(
        category: str | None = None,
        db: Session = Depends(get_db)
) -> list[FoodItemRead]:
    """Retrieve all food items, optionally filtered by category."""
    food_items = crud_inventory.get_all_food_items(db, category=category)
    return [FoodItemRead.model_validate(item, from_attributes=True) for item in food_items]


@food_items_router.get(
    "/{food_item_id}",
    response_model=FoodItemRead,
    status_code=status.HTTP_200_OK,
    summary="Get a food item by ID",
)
def get_food_item(
        food_item_id: int,
        db: Session = Depends(get_db)
) -> FoodItemRead:
    """Retrieve a single food item by primary key."""
    food_item = crud_inventory.get_food_item_by_id(db, food_item_id)
    if food_item is None:
        raise HTTPException(status_code=404, detail="Food item not found.")

    return FoodItemRead.model_validate(food_item, from_attributes=True)


@food_items_router.put(
    "/{food_item_id}",
    response_model=FoodItemRead,
    status_code=status.HTTP_200_OK,
    summary="Update a food item",
)
def update_food_item(
        food_item_id: int,
        food_item_data: FoodItemUpdate,
        db: Session = Depends(get_db),
) -> FoodItemRead:
    """Update an existing food item (partial update)."""
    try:
        updated_food_item = crud_inventory.update_food_item(db, food_item_id, food_item_data)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FoodItemRead.model_validate(updated_food_item, from_attributes=True)


@food_items_router.delete(
    "/{food_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a food item",
)
def delete_food_item(
        food_item_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a food item by primary key."""
    try:
        crud_inventory.delete_food_item(db, food_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# GLOBAL: Direct Inventory Item Operations                          #
# ================================================================== #

@inventory_items_router.get(
    "/{inventory_id}",
    response_model=InventoryItemRead,
    status_code=status.HTTP_200_OK,
    summary="Get an inventory item by ID",
)
def get_inventory_item(
        inventory_id: int,
        db: Session = Depends(get_db),
) -> InventoryItemRead:
    """Get an inventory item by its global ID."""
    item = crud_inventory.get_inventory_item_by_id(db, inventory_id)
    if item is None:
        raise HTTPException(404, f"Inventory item with ID {inventory_id} not found")
    return InventoryItemRead.model_validate(item, from_attributes=True)


@inventory_items_router.put(
    "/{inventory_id}",
    response_model=InventoryItemRead,
    status_code=status.HTTP_200_OK,
    summary="Update an inventory item",
)
def update_inventory_item(
        inventory_id: int,
        inventory_data: InventoryItemUpdate,
        db: Session = Depends(get_db),
) -> InventoryItemRead:
    """Update an existing inventory item globally."""
    try:
        updated_item = crud_inventory.update_inventory_item(db, inventory_id, inventory_data)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Refresh to get computed properties
    inventory_item = crud_inventory.get_inventory_item_by_id(db, updated_item.id)
    return InventoryItemRead.model_validate(inventory_item, from_attributes=True)


@inventory_items_router.delete(
    "/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an inventory item",
)
def delete_inventory_item(
        inventory_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete an inventory item globally."""
    try:
        crud_inventory.delete_inventory_item(db, inventory_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# GLOBAL: Direct Storage Operations                                 #
# ================================================================== #

@storage_router.get(
    "/{storage_id}",
    response_model=StorageLocationRead,
    status_code=status.HTTP_200_OK,
    summary="Get a storage location by ID",
)
def get_storage_location(
        storage_id: int,
        db: Session = Depends(get_db),
) -> StorageLocationRead:
    """Get a storage location by its global ID."""
    storage = crud_inventory.get_storage_location_by_id(db, storage_id)
    if storage is None:
        raise HTTPException(404, f"Storage location with ID {storage_id} not found")
    return StorageLocationRead.model_validate(storage, from_attributes=True)


@storage_router.put(
    "/{storage_id}",
    response_model=StorageLocationRead,
    status_code=status.HTTP_200_OK,
    summary="Update a storage location",
)
def update_storage_location(
        storage_id: int,
        storage_data: StorageLocationUpdate,
        db: Session = Depends(get_db),
) -> StorageLocationRead:
    """Update an existing storage location globally."""
    try:
        updated_storage = crud_inventory.update_storage_location(db, storage_id, storage_data)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StorageLocationRead.model_validate(updated_storage, from_attributes=True)


@storage_router.delete(
    "/{storage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a storage location",
)
def delete_storage_location(
        storage_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a storage location globally."""
    try:
        crud_inventory.delete_storage_location(db, storage_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Export routers for backwards compatibility                        #
# ================================================================== #

# Main router for backwards compatibility
router = kitchen_router