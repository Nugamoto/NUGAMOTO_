"""FastAPI router exposing the */inventory* endpoints."""

from __future__ import annotations

from typing import Optional

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

router = APIRouter(tags=["Inventory"])


# ------------------------------------------------------------------ #
# FoodItem Routes                                                    #
# ------------------------------------------------------------------ #

@router.post(
    "/fooditems/",
    response_model=FoodItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new food item",
)
def create_food_item(
        food_item_data: FoodItemCreate, db: Session = Depends(get_db)
) -> FoodItemRead:
    """Create a new global food item.

    Food items are global entities that can be used across all kitchens.
    They represent basic food categories like "Tomato", "Rice", etc.

    Args:
        food_item_data: Validated food item payload.
        db: Injected database session.

    Returns:
        The newly created food item.

    Raises:
        HTTPException: 400 if a food item with the same name already exists.
    """
    try:
        db_food_item = crud_inventory.create_food_item(db, food_item_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FoodItemRead.model_validate(db_food_item, from_attributes=True)


@router.get(
    "/fooditems/",
    response_model=list[FoodItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get all food items",
)
def get_all_food_items(
        category: Optional[str] = None, db: Session = Depends(get_db)
) -> list[FoodItemRead]:
    """Retrieve all food items, optionally filtered by category.

    Args:
        category: Optional category filter.
        db: Injected database session.

    Returns:
        A list of all food items, optionally filtered by category.
    """
    food_items = crud_inventory.get_all_food_items(db, category=category)
    return [FoodItemRead.model_validate(item, from_attributes=True) for item in food_items]


@router.get(
    "/fooditems/{food_item_id}",
    response_model=FoodItemRead,
    status_code=status.HTTP_200_OK,
    summary="Get a food item by ID",
)
def get_food_item(food_item_id: int, db: Session = Depends(get_db)) -> FoodItemRead:
    """Retrieve a single food item by primary key.

    Args:
        food_item_id: Primary key of the food item.
        db: Injected database session.

    Returns:
        The requested food item.

    Raises:
        HTTPException: 404 if the food item does not exist.
    """
    food_item = crud_inventory.get_food_item_by_id(db, food_item_id)
    if food_item is None:
        raise HTTPException(status_code=404, detail="Food item not found.")

    return FoodItemRead.model_validate(food_item, from_attributes=True)


@router.put(
    "/fooditems/{food_item_id}",
    response_model=FoodItemRead,
    status_code=status.HTTP_200_OK,
    summary="Update a food item",
)
def update_food_item(
        food_item_id: int,
        food_item_data: FoodItemUpdate,
        db: Session = Depends(get_db),
) -> FoodItemRead:
    """Update an existing food item (partial update).

    Args:
        food_item_id: Primary key of the food item to update.
        food_item_data: Partial food item payload.
        db: Injected database session.

    Returns:
        The updated food item.

    Raises:
        HTTPException:
            * 404 if the food item does not exist.
            * 400 if name conflict occurs.
    """
    try:
        updated_food_item = crud_inventory.update_food_item(db, food_item_id, food_item_data)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FoodItemRead.model_validate(updated_food_item, from_attributes=True)


@router.delete(
    "/fooditems/{food_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a food item",
)
def delete_food_item(
        food_item_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a food item by primary key.

    Args:
        food_item_id: ID of the food item to delete.
        db: Injected database session.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the food item does not exist.
    """
    try:
        crud_inventory.delete_food_item(db, food_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ #
# StorageLocation Routes                                             #
# ------------------------------------------------------------------ #

@router.post(
    "/kitchens/{kitchen_id}/storage/",
    response_model=StorageLocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new storage location",
)
def create_storage_location(
        kitchen_id: int,
        storage_data: StorageLocationCreate,
        db: Session = Depends(get_db),
) -> StorageLocationRead:
    """Create a new storage location for a kitchen.

    Storage locations are kitchen-specific places where food can be stored,
    such as "Fridge", "Pantry", "Freezer", etc.

    Args:
        kitchen_id: Primary key of the kitchen.
        storage_data: Validated storage location payload.
        db: Injected database session.

    Returns:
        The newly created storage location.

    Raises:
        HTTPException:
            * 404 if the kitchen does not exist.
            * 400 if a storage location with the same name already exists in this kitchen.
    """
    try:
        db_storage = crud_inventory.create_storage_location(db, kitchen_id, storage_data)
    except ValueError as exc:
        if "Kitchen not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StorageLocationRead.model_validate(db_storage, from_attributes=True)


@router.get(
    "/kitchens/{kitchen_id}/storage/",
    response_model=list[StorageLocationRead],
    status_code=status.HTTP_200_OK,
    summary="Get all storage locations for a kitchen",
)
def get_kitchen_storage_locations(
        kitchen_id: int, db: Session = Depends(get_db)
) -> list[StorageLocationRead]:
    """Retrieve all storage locations for a kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        db: Injected database session.

    Returns:
        A list of all storage locations for the kitchen.
    """
    storage_locations = crud_inventory.get_kitchen_storage_locations(db, kitchen_id)
    return [
        StorageLocationRead.model_validate(storage, from_attributes=True)
        for storage in storage_locations
    ]


@router.put(
    "/storage/{storage_id}",
    response_model=StorageLocationRead,
    status_code=status.HTTP_200_OK,
    summary="Update a storage location",
)
def update_storage_location(
        storage_id: int,
        storage_data: StorageLocationUpdate,
        db: Session = Depends(get_db),
) -> StorageLocationRead:
    """Update an existing storage location (partial update).

    Args:
        storage_id: Primary key of the storage location to update.
        storage_data: Partial storage location payload.
        db: Injected database session.

    Returns:
        The updated storage location.

    Raises:
        HTTPException:
            * 404 if the storage location does not exist.
            * 400 if name conflict occurs.
    """
    try:
        updated_storage = crud_inventory.update_storage_location(db, storage_id, storage_data)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StorageLocationRead.model_validate(updated_storage, from_attributes=True)


@router.delete(
    "/storage/{storage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a storage location",
)
def delete_storage_location(
        storage_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a storage location by primary key.

    Args:
        storage_id: ID of the storage location to delete.
        db: Injected database session.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the storage location does not exist.
    """
    try:
        crud_inventory.delete_storage_location(db, storage_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ #
# InventoryItem Routes                                               #
# ------------------------------------------------------------------ #

@router.post(
    "/kitchens/{kitchen_id}/inventory/",
    response_model=InventoryItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an inventory item",
)
def add_inventory_item(
        kitchen_id: int,
        inventory_data: InventoryItemCreate,
        db: Session = Depends(get_db),
) -> InventoryItemRead:
    """Add a new inventory item or update existing quantity.

    If an inventory item already exists for the same kitchen, food item,
    and storage location, the quantities will be added together.

    Args:
        kitchen_id: Primary key of the kitchen.
        inventory_data: Validated inventory item payload.
        db: Injected database session.

    Returns:
        The created or updated inventory item.

    Raises:
        HTTPException:
            * 404 if the kitchen, food item, or storage location does not exist.
            * 400 if the storage location does not belong to the kitchen.

    Note:
        This endpoint is designed for easy integration with AI services
        that manage inventory automatically based on recipes and usage patterns.
    """
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


@router.get(
    "/kitchens/{kitchen_id}/inventory/",
    response_model=KitchenInventorySummary,
    status_code=status.HTTP_200_OK,
    summary="Get complete kitchen inventory",
)
def get_kitchen_inventory(
        kitchen_id: int, db: Session = Depends(get_db)
) -> KitchenInventorySummary:
    """Retrieve complete kitchen inventory grouped by storage location.

    This endpoint provides a comprehensive view of the kitchen's inventory
    organized by storage location with summary statistics. It's optimized
    for UI display and AI analysis.

    Args:
        kitchen_id: Primary key of the kitchen.
        db: Injected database session.

    Returns:
        Complete inventory summary grouped by storage location with statistics.

    Note:
        This endpoint is designed to be consumed by AI services for
        recipe generation and shopping list automation. The grouped format
        makes it easy to understand what ingredients are available and where
        they are stored.
    """
    inventory_summary = crud_inventory.get_kitchen_inventory_grouped_by_storage(
        db, kitchen_id
    )
    return inventory_summary


@router.get(
    "/kitchens/{kitchen_id}/inventory/low-stock",
    response_model=list[InventoryItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get low stock items",
)
def get_low_stock_items(
        kitchen_id: int, db: Session = Depends(get_db)
) -> list[InventoryItemRead]:
    """Retrieve all inventory items that are below their minimum quantity.

    Args:
        kitchen_id: Primary key of the kitchen.
        db: Injected database session.

    Returns:
        A list of inventory items that are below their minimum quantity.

    Note:
        This endpoint is designed for integration with AI services for
        automatic shopping list generation when items run low.
    """
    low_stock_items = crud_inventory.get_low_stock_items(db, kitchen_id)
    return [
        InventoryItemRead.model_validate(item, from_attributes=True)
        for item in low_stock_items
    ]


@router.get(
    "/kitchens/{kitchen_id}/inventory/expiring",
    response_model=list[InventoryItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get expiring items",
)
def get_expiring_items(
        kitchen_id: int, days: int = 3, db: Session = Depends(get_db)
) -> list[InventoryItemRead]:
    """Retrieve all inventory items that expire within the specified number of days.

    Args:
        kitchen_id: Primary key of the kitchen.
        days: Number of days to look ahead (default: 3).
        db: Injected database session.

    Returns:
        A list of inventory items that expire within the specified timeframe.

    Note:
        This endpoint can be integrated with AI services for meal planning
        to prioritize ingredients that are about to expire, helping reduce
        food waste.
    """
    expiring_items = crud_inventory.get_expiring_items(db, kitchen_id, days)
    return [
        InventoryItemRead.model_validate(item, from_attributes=True)
        for item in expiring_items
    ]


@router.put(
    "/inventory/{inventory_id}",
    response_model=InventoryItemRead,
    status_code=status.HTTP_200_OK,
    summary="Update an inventory item",
)
def update_inventory_item(
        inventory_id: int,
        inventory_data: InventoryItemUpdate,
        db: Session = Depends(get_db),
) -> InventoryItemRead:
    """Update an existing inventory item (partial update).

    Args:
        inventory_id: Primary key of the inventory item to update.
        inventory_data: Partial inventory item payload.
        db: Injected database session.

    Returns:
        The updated inventory item.

    Raises:
        HTTPException:
            * 404 if the inventory item does not exist.
            * 400 if validation fails.
    """
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


@router.delete(
    "/inventory/{inventory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an inventory item",
)
def delete_inventory_item(
        inventory_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete an inventory item by primary key.

    Args:
        inventory_id: ID of the inventory item to delete.
        db: Injected database session.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the inventory item does not exist.
    """
    try:
        crud_inventory.delete_inventory_item(db, inventory_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)