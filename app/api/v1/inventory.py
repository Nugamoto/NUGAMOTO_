"""FastAPI router exposing the inventory endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import inventory as crud_inventory
from app.schemas.inventory import (
    FoodItemCreate, FoodItemRead, FoodItemUpdate,
    StorageLocationCreate, StorageLocationRead, StorageLocationUpdate,
    InventoryItemCreate, InventoryItemRead, InventoryItemUpdate,
    KitchenInventorySummary
)

# Create sub-routers for better organization
kitchen_router = APIRouter(prefix="/kitchens", tags=["Kitchen Inventory"])
food_items_router = APIRouter(prefix="/food-items", tags=["Food Items"])
inventory_items_router = APIRouter(prefix="/inventory", tags=["Inventory Items"])
storage_router = APIRouter(prefix="/storage", tags=["Storage Locations"])


# ------------------------------------------------------------------ #
# Storage Location Endpoints                                         #
# ------------------------------------------------------------------ #

@storage_router.post(
    "/kitchens/{kitchen_id}/locations/",
    response_model=StorageLocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new storage location",
)
def create_storage_location(
        kitchen_id: int,
        storage_data: StorageLocationCreate,
        db: Session = Depends(get_db),
) -> StorageLocationRead:
    """Create a new storage location for a specific kitchen.

    Args:
        kitchen_id: The ID of the kitchen.
        storage_data: Storage location data.
        db: Injected database session.

    Returns:
        The newly created storage location.

    Example:
        ```json
        {
            "name": "Refrigerator"
        }
        ```
    """
    db_storage = crud_inventory.create_storage_location(db, kitchen_id, storage_data)
    return StorageLocationRead.model_validate(db_storage, from_attributes=True)


@kitchen_router.get(
    "/{kitchen_id}/storage-locations/",
    response_model=list[StorageLocationRead],
    status_code=status.HTTP_200_OK,
    summary="Get all storage locations for a kitchen",
)
def get_kitchen_storage_locations(
        kitchen_id: int,
        db: Session = Depends(get_db),
) -> list[StorageLocationRead]:
    """Retrieve all storage locations for a specific kitchen."""
    storage_locations = crud_inventory.get_kitchen_storage_locations(db, kitchen_id)
    return [
        StorageLocationRead.model_validate(location, from_attributes=True)
        for location in storage_locations
    ]


# ------------------------------------------------------------------ #
# Inventory Item Endpoints                                           #
# ------------------------------------------------------------------ #

@kitchen_router.post(
    "/{kitchen_id}/inventory/",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to kitchen inventory",
)
def add_inventory_item(
        kitchen_id: int,
        inventory_data: InventoryItemCreate,
        db: Session = Depends(get_db),
) -> InventoryItemRead:
    """Add a new item to the kitchen inventory.

    The quantity should be provided in the food item's base unit.
    If an item with the same food_item_id and storage_location_id already exists,
    the quantities will be combined.

    Args:
        kitchen_id: The ID of the kitchen.
        inventory_data: Inventory item data with quantity in base unit.
        db: Injected database session.

    Returns:
        The created or updated inventory item.

    Example:
        ```json
        {
            "food_item_id": 1,
            "storage_location_id": 2,
            "quantity": 500.0,
            "min_quantity": 100.0,
            "expiration_date": "2024-12-31"
        }
        ```

    Note:
        - quantity: Amount in the food item's base unit (e.g., grams, ml, pieces)
        - min_quantity: Minimum threshold in base unit for low stock alerts
        - Future versions will support unit conversion from input units
    """
    try:
        db_inventory = crud_inventory.create_or_update_inventory_item(
            db, kitchen_id, inventory_data
        )
        return InventoryItemRead.model_validate(db_inventory, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@kitchen_router.get(
    "/{kitchen_id}/inventory/",
    response_model=list[InventoryItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get kitchen inventory",
)
def get_kitchen_inventory(
        kitchen_id: int,
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
        db: Session = Depends(get_db),
) -> list[InventoryItemRead]:
    """Retrieve all inventory items for a specific kitchen.

    Returns items with their related food item and storage location information.
    All quantities are shown in the respective food item's base unit.
    """
    inventory_items = crud_inventory.get_kitchen_inventory(db, kitchen_id, skip, limit)
    return [
        InventoryItemRead.model_validate(item, from_attributes=True)
        for item in inventory_items
    ]


@kitchen_router.get(
    "/{kitchen_id}/inventory/summary/",
    response_model=KitchenInventorySummary,
    status_code=status.HTTP_200_OK,
    summary="Get kitchen inventory summary",
)
def get_kitchen_inventory_summary(
        kitchen_id: int,
        db: Session = Depends(get_db),
) -> KitchenInventorySummary:
    """Get a complete summary of kitchen inventory grouped by storage locations.

    Includes statistics about low stock, expired, and expiring items.
    """
    return crud_inventory.get_kitchen_inventory_grouped_by_storage(db, kitchen_id)


@kitchen_router.get(
    "/{kitchen_id}/inventory/low-stock/",
    response_model=list[InventoryItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get low stock items",
)
def get_low_stock_items(
        kitchen_id: int,
        db: Session = Depends(get_db),
) -> list[InventoryItemRead]:
    """Retrieve all inventory items that are below their minimum quantity threshold.

    Useful for generating shopping lists and restocking alerts.
    """
    low_stock_items = crud_inventory.get_low_stock_items(db, kitchen_id)
    return [
        InventoryItemRead.model_validate(item, from_attributes=True)
        for item in low_stock_items
    ]


@kitchen_router.get(
    "/{kitchen_id}/inventory/expiring/",
    response_model=list[InventoryItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get expiring items",
)
def get_expiring_items(
        kitchen_id: int,
        days: int = Query(
            5, ge=1, le=365,
            description="Number of days ahead to check for expiring items"
        ),
        db: Session = Depends(get_db),
) -> list[InventoryItemRead]:
    """Retrieve all inventory items that expire within the specified number of days.

    Useful for food waste prevention and meal planning.
    """
    expiring_items = crud_inventory.get_expiring_items(db, kitchen_id, days)
    return [
        InventoryItemRead.model_validate(item, from_attributes=True)
        for item in expiring_items
    ]


# ------------------------------------------------------------------ #
# Food Item Endpoints                                                #
# ------------------------------------------------------------------ #

@food_items_router.post(
    "/",
    response_model=FoodItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new food item",
)
def create_food_item(
        food_item_data: FoodItemCreate,
        db: Session = Depends(get_db),
) -> FoodItemRead:
    """Create a new global food item.

    Food items are shared across all kitchens and define the base unit
    for quantity measurements.

    Args:
        food_item_data: Food item data including base_unit_id.
        db: Injected database session.

    Returns:
        The newly created food item.

    Example:
        ```json
        {
            "name": "Tomato",
            "category": "Vegetables",
            "base_unit_id": 1
        }
        ```

    Note:
        - base_unit_id: Reference to the unit table defining the base measurement unit
        - All inventory quantities for this food item will be stored in this unit
    """
    try:
        db_food_item = crud_inventory.create_food_item(db, food_item_data)
        return FoodItemRead.model_validate(db_food_item, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@food_items_router.get(
    "/",
    response_model=list[FoodItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get all food items",
)
def get_all_food_items(
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
        db: Session = Depends(get_db),
) -> list[FoodItemRead]:
    """Retrieve all available food items.

    Returns global food items that can be used across all kitchens.
    """
    food_items = crud_inventory.get_all_food_items(db, skip, limit)
    return [
        FoodItemRead.model_validate(item, from_attributes=True)
        for item in food_items
    ]


@food_items_router.get(
    "/{food_item_id}",
    response_model=FoodItemRead,
    status_code=status.HTTP_200_OK,
    summary="Get a food item by ID",
)
def get_food_item(
        food_item_id: int,
        db: Session = Depends(get_db),
) -> FoodItemRead:
    """Retrieve a specific food item by its ID."""
    food_item = crud_inventory.get_food_item_by_id(db, food_item_id)
    if food_item is None:
        raise HTTPException(404, f"Food item with ID {food_item_id} not found")
    return FoodItemRead.model_validate(food_item, from_attributes=True)


@food_items_router.patch(
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
    """Update an existing food item.

    Note: Changing the base_unit_id will affect all existing inventory items
    for this food item, as their quantities are stored in the base unit.
    """
    try:
        updated_item = crud_inventory.update_food_item(db, food_item_id, food_item_data)
        if updated_item is None:
            raise HTTPException(404, f"Food item with ID {food_item_id} not found")
        return FoodItemRead.model_validate(updated_item, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@food_items_router.delete(
    "/{food_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a food item",
)
def delete_food_item(
        food_item_id: int,
        db: Session = Depends(get_db),
) -> None:
    """Delete a food item.

    This will fail if the food item is referenced by any inventory items.
    """
    success = crud_inventory.delete_food_item(db, food_item_id)
    if not success:
        raise HTTPException(404, f"Food item with ID {food_item_id} not found")


# ------------------------------------------------------------------ #
# Individual Inventory Item Endpoints                                #
# ------------------------------------------------------------------ #

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
    """Get an inventory item by its global ID.

    Returns the item with related food item and storage location information.
    Quantity is shown in the food item's base unit.
    """
    item = crud_inventory.get_inventory_item_by_id(db, inventory_id)
    if item is None:
        raise HTTPException(404, f"Inventory item with ID {inventory_id} not found")
    return InventoryItemRead.model_validate(item, from_attributes=True)


@inventory_items_router.patch(
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
    """Update an existing inventory item.

    Args:
        inventory_id: The ID of the inventory item to update.
        inventory_data: Updated data with quantities in base unit.
        db: Injected database session.

    Returns:
        The updated inventory item.

    Note:
        - quantity: New amount in the food item's base unit
        - This completely replaces the existing quantity (does not add to it)
    """
    try:
        updated_item = crud_inventory.update_inventory_item(db, inventory_id, inventory_data)
        if updated_item is None:
            raise HTTPException(404, f"Inventory item with ID {inventory_id} not found")
        return InventoryItemRead.model_validate(updated_item, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@inventory_items_router.delete(
    "/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an inventory item",
)
def delete_inventory_item(
        inventory_id: int,
        db: Session = Depends(get_db),
) -> None:
    """Delete an inventory item completely."""
    success = crud_inventory.delete_inventory_item(db, inventory_id)
    if not success:
        raise HTTPException(404, f"Inventory item with ID {inventory_id} not found")


# ------------------------------------------------------------------ #
# Storage Location Management                                        #
# ------------------------------------------------------------------ #

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
    """Get a storage location by its ID."""
    storage = crud_inventory.get_storage_location_by_id(db, storage_id)
    if storage is None:
        raise HTTPException(404, f"Storage location with ID {storage_id} not found")
    return StorageLocationRead.model_validate(storage, from_attributes=True)


@storage_router.patch(
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
    """Update an existing storage location."""
    updated_storage = crud_inventory.update_storage_location(db, storage_id, storage_data)
    if updated_storage is None:
        raise HTTPException(404, f"Storage location with ID {storage_id} not found")
    return StorageLocationRead.model_validate(updated_storage, from_attributes=True)


@storage_router.delete(
    "/{storage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a storage location",
)
def delete_storage_location(
        storage_id: int,
        db: Session = Depends(get_db),
) -> None:
    """Delete a storage location.

    This will fail if the storage location contains any inventory items.
    """
    success = crud_inventory.delete_storage_location(db, storage_id)
    if not success:
        raise HTTPException(404, f"Storage location with ID {storage_id} not found")


# Main router that includes all sub-routers
router = APIRouter()
router.include_router(kitchen_router)
router.include_router(food_items_router)
router.include_router(inventory_items_router)
router.include_router(storage_router)
