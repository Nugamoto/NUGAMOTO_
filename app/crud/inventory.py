"""CRUD helper functions for inventory management."""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.inventory import FoodItem, InventoryItem, StorageLocation
from app.models.kitchen import Kitchen
from app.schemas.inventory import (
    FoodItemCreate,
    FoodItemUpdate,
    InventoryItemCreate,
    InventoryItemUpdate,
    KitchenInventorySummary,
    StorageLocationCreate,
    StorageLocationUpdate,
    StorageLocationWithInventory,
)


# ------------------------------------------------------------------ #
# FoodItem CRUD                                                      #
# ------------------------------------------------------------------ #

def create_food_item(db: Session, food_item_data: FoodItemCreate) -> FoodItem:
    """Create and persist a new food item.

    Args:
        db: Database session.
        food_item_data: Validated food item payload.

    Returns:
        The newly created, *refreshed* food item instance.

    Raises:
        ValueError: If a food item with the same name already exists.
    """
    # Check if food item with same name already exists
    existing_stmt = select(FoodItem).where(FoodItem.name == food_item_data.name)
    if db.scalar(existing_stmt) is not None:
        raise ValueError(f"Food item with name '{food_item_data.name}' already exists.")

    new_food_item = FoodItem(
        name=food_item_data.name,
        category=food_item_data.category,
        unit=food_item_data.unit,
    )
    db.add(new_food_item)
    db.commit()
    db.refresh(new_food_item)
    return new_food_item


def get_food_item_by_id(db: Session, food_item_id: int) -> FoodItem | None:
    """Return a food item by primary key.

    Args:
        db: Database session.
        food_item_id: Primary key of the food item.

    Returns:
        The matching food item or ``None``.
    """
    stmt = select(FoodItem).where(FoodItem.id == food_item_id)
    return db.scalar(stmt)


def get_food_item_by_name(db: Session, name: str) -> FoodItem | None:
    """Return a food item by name.

    Args:
        db: Database session.
        name: Name of the food item.

    Returns:
        The matching food item or ``None``.
    """
    stmt = select(FoodItem).where(FoodItem.name == name)
    return db.scalar(stmt)


def get_all_food_items(db: Session, category: Optional[str] = None) -> list[FoodItem]:
    """Return all food items, optionally filtered by category.

    Args:
        db: Database session.
        category: Optional category filter.

    Returns:
        A list of food items.
    """
    stmt = select(FoodItem)
    if category:
        stmt = stmt.where(FoodItem.category == category)
    return list(db.scalars(stmt).all())


def update_food_item(
        db: Session, food_item_id: int, food_item_data: FoodItemUpdate
) -> FoodItem:
    """Update an existing food item with partial data.

    Args:
        db: Active database session.
        food_item_id: Primary key of the target food item.
        food_item_data: Validated payload containing partial food item data.

    Returns:
        The updated and refreshed food item instance.

    Raises:
        ValueError: If the food item does not exist or name conflict occurs.
    """
    food_item = get_food_item_by_id(db, food_item_id)
    if food_item is None:
        raise ValueError("Food item not found.")

    # Check for name conflicts if name is being updated
    if food_item_data.name is not None and food_item_data.name != food_item.name:
        existing_stmt = select(FoodItem).where(FoodItem.name == food_item_data.name)
        if db.scalar(existing_stmt) is not None:
            raise ValueError(f"Food item with name '{food_item_data.name}' already exists.")

    # Update fields
    if food_item_data.name is not None:
        food_item.name = food_item_data.name
    if food_item_data.category is not None:
        food_item.category = food_item_data.category
    if food_item_data.unit is not None:
        food_item.unit = food_item_data.unit

    db.commit()
    db.refresh(food_item)
    return food_item


def delete_food_item(db: Session, food_item_id: int) -> None:
    """Remove a food item from the database.

    Args:
        db: Active database session.
        food_item_id: Primary key of the food item to delete.

    Raises:
        ValueError: If the food item does not exist.
    """
    food_item = get_food_item_by_id(db, food_item_id)
    if food_item is None:
        raise ValueError("Food item not found.")

    db.delete(food_item)
    db.commit()


# ------------------------------------------------------------------ #
# StorageLocation CRUD                                               #
# ------------------------------------------------------------------ #

def create_storage_location(
        db: Session, kitchen_id: int, storage_data: StorageLocationCreate
) -> StorageLocation:
    """Create and persist a new storage location for a kitchen.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        storage_data: Validated storage location payload.

    Returns:
        The newly created, *refreshed* storage location instance.

    Raises:
        ValueError: If the kitchen does not exist or storage location name conflicts.
    """
    # Check if kitchen exists
    kitchen_stmt = select(Kitchen).where(Kitchen.id == kitchen_id)
    if db.scalar(kitchen_stmt) is None:
        raise ValueError("Kitchen not found.")

    # Check for name conflicts within the kitchen
    existing_stmt = select(StorageLocation).where(
        StorageLocation.kitchen_id == kitchen_id,
        StorageLocation.name == storage_data.name,
        )
    if db.scalar(existing_stmt) is not None:
        raise ValueError(
            f"Storage location with name '{storage_data.name}' already exists in this kitchen."
        )

    new_storage = StorageLocation(
        kitchen_id=kitchen_id,
        name=storage_data.name,
    )
    db.add(new_storage)
    db.commit()
    db.refresh(new_storage)
    return new_storage


def get_storage_location_by_id(db: Session, storage_id: int) -> StorageLocation | None:
    """Return a storage location by primary key.

    Args:
        db: Database session.
        storage_id: Primary key of the storage location.

    Returns:
        The matching storage location or ``None``.
    """
    stmt = select(StorageLocation).where(StorageLocation.id == storage_id)
    return db.scalar(stmt)


def get_kitchen_storage_locations(db: Session, kitchen_id: int) -> list[StorageLocation]:
    """Return all storage locations for a kitchen.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        A list of storage locations for the kitchen.
    """
    stmt = select(StorageLocation).where(StorageLocation.kitchen_id == kitchen_id)
    return list(db.scalars(stmt).all())


def update_storage_location(
        db: Session, storage_id: int, storage_data: StorageLocationUpdate
) -> StorageLocation:
    """Update an existing storage location with partial data.

    Args:
        db: Active database session.
        storage_id: Primary key of the target storage location.
        storage_data: Validated payload containing partial storage location data.

    Returns:
        The updated and refreshed storage location instance.

    Raises:
        ValueError: If the storage location does not exist or name conflict occurs.
    """
    storage = get_storage_location_by_id(db, storage_id)
    if storage is None:
        raise ValueError("Storage location not found.")

    # Check for name conflicts if name is being updated
    if storage_data.name is not None and storage_data.name != storage.name:
        existing_stmt = select(StorageLocation).where(
            StorageLocation.kitchen_id == storage.kitchen_id,
            StorageLocation.name == storage_data.name,
            )
        if db.scalar(existing_stmt) is not None:
            raise ValueError(
                f"Storage location with name '{storage_data.name}' already exists in this kitchen."
            )

    # Update fields
    if storage_data.name is not None:
        storage.name = storage_data.name

    db.commit()
    db.refresh(storage)
    return storage


def delete_storage_location(db: Session, storage_id: int) -> None:
    """Remove a storage location from the database.

    Args:
        db: Active database session.
        storage_id: Primary key of the storage location to delete.

    Raises:
        ValueError: If the storage location does not exist.
    """
    storage = get_storage_location_by_id(db, storage_id)
    if storage is None:
        raise ValueError("Storage location not found.")

    db.delete(storage)
    db.commit()


# ------------------------------------------------------------------ #
# InventoryItem CRUD                                                 #
# ------------------------------------------------------------------ #

def create_or_update_inventory_item(
        db: Session, kitchen_id: int, inventory_data: InventoryItemCreate
) -> InventoryItem:
    """Create a new inventory item or update existing one.

    If an inventory item already exists for the same kitchen, food item,
    and storage location, the quantities will be added together.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        inventory_data: Validated inventory item payload.

    Returns:
        The created or updated inventory item instance.

    Raises:
        ValueError: If referenced entities do not exist or don't belong to the kitchen.
    """
    # Validate kitchen exists
    kitchen_stmt = select(Kitchen).where(Kitchen.id == kitchen_id)
    if db.scalar(kitchen_stmt) is None:
        raise ValueError("Kitchen not found.")

    # Validate food item exists
    food_item_stmt = select(FoodItem).where(FoodItem.id == inventory_data.food_item_id)
    if db.scalar(food_item_stmt) is None:
        raise ValueError("Food item not found.")

    # Validate storage location exists and belongs to kitchen
    storage_stmt = select(StorageLocation).where(
        StorageLocation.id == inventory_data.storage_location_id,
        StorageLocation.kitchen_id == kitchen_id,
        )
    if db.scalar(storage_stmt) is None:
        raise ValueError("Storage location not found or does not belong to this kitchen.")

    # Check if inventory item already exists
    existing_stmt = select(InventoryItem).where(
        InventoryItem.kitchen_id == kitchen_id,
        InventoryItem.food_item_id == inventory_data.food_item_id,
        InventoryItem.storage_location_id == inventory_data.storage_location_id,
        )
    existing_item = db.scalar(existing_stmt)

    if existing_item:
        # Update existing item by adding quantities
        existing_item.quantity += inventory_data.quantity
        if inventory_data.min_quantity is not None:
            existing_item.min_quantity = inventory_data.min_quantity
        if inventory_data.expiration_date is not None:
            # Keep the earlier expiration date
            if existing_item.expiration_date is None:
                existing_item.expiration_date = inventory_data.expiration_date
            else:
                existing_item.expiration_date = min(
                    existing_item.expiration_date, inventory_data.expiration_date
                )

        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        # Create new inventory item
        new_item = InventoryItem(
            kitchen_id=kitchen_id,
            food_item_id=inventory_data.food_item_id,
            storage_location_id=inventory_data.storage_location_id,
            quantity=inventory_data.quantity,
            min_quantity=inventory_data.min_quantity,
            expiration_date=inventory_data.expiration_date,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        return new_item


def get_inventory_item_by_id(db: Session, inventory_id: int) -> InventoryItem | None:
    """Return an inventory item by primary key with related data.

    Args:
        db: Database session.
        inventory_id: Primary key of the inventory item.

    Returns:
        The matching inventory item with related data or ``None``.
    """
    stmt = (
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item),
            selectinload(InventoryItem.storage_location),
        )
        .where(InventoryItem.id == inventory_id)
    )
    return db.scalar(stmt)


def get_kitchen_inventory(db: Session, kitchen_id: int) -> list[InventoryItem]:
    """Return all inventory items for a kitchen with related data.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        A list of inventory items with related data.
    """
    stmt = (
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item),
            selectinload(InventoryItem.storage_location),
        )
        .where(InventoryItem.kitchen_id == kitchen_id)
    )
    return list(db.scalars(stmt).all())


def get_kitchen_inventory_grouped_by_storage(
        db: Session, kitchen_id: int
) -> KitchenInventorySummary:
    """Return kitchen inventory grouped by storage location with summary stats.

    This function is optimized for UI display and AI analysis by providing
    a structured view of the kitchen's inventory organized by storage location.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        A complete inventory summary grouped by storage location.

    Note:
        This function is designed to be consumed by AI services for
        recipe generation and shopping list automation.
    """
    # Get all storage locations for the kitchen with their inventory items
    stmt = (
        select(StorageLocation)
        .options(
            selectinload(StorageLocation.inventory_items).selectinload(
                InventoryItem.food_item
            )
        )
        .where(StorageLocation.kitchen_id == kitchen_id)
    )
    storage_locations = list(db.scalars(stmt).all())

    # Calculate summary statistics
    total_items = 0
    low_stock_items = 0
    expired_items = 0
    expires_soon_items = 0

    storage_with_inventory = []
    for storage in storage_locations:
        inventory_items = []
        for item in storage.inventory_items:
            total_items += 1
            if item.is_low_stock:
                low_stock_items += 1
            if item.is_expired:
                expired_items += 1
            if item.expires_soon:
                expires_soon_items += 1

            inventory_items.append(item)

        storage_with_inventory.append(
            StorageLocationWithInventory(
                id=storage.id,
                kitchen_id=storage.kitchen_id,
                name=storage.name,
                inventory_items=inventory_items,
            )
        )

    return KitchenInventorySummary(
        kitchen_id=kitchen_id,
        storage_locations=storage_with_inventory,
        total_items=total_items,
        low_stock_items=low_stock_items,
        expired_items=expired_items,
        expires_soon_items=expires_soon_items,
    )


def update_inventory_item(
        db: Session, inventory_id: int, inventory_data: InventoryItemUpdate
) -> InventoryItem:
    """Update an existing inventory item with partial data.

    Args:
        db: Active database session.
        inventory_id: Primary key of the target inventory item.
        inventory_data: Validated payload containing partial inventory item data.

    Returns:
        The updated and refreshed inventory item instance.

    Raises:
        ValueError: If the inventory item does not exist or validation fails.
    """
    item = get_inventory_item_by_id(db, inventory_id)
    if item is None:
        raise ValueError("Inventory item not found.")

    # Validate foreign keys if they're being updated
    if inventory_data.food_item_id is not None:
        food_item_stmt = select(FoodItem).where(FoodItem.id == inventory_data.food_item_id)
        if db.scalar(food_item_stmt) is None:
            raise ValueError("Food item not found.")

    if inventory_data.storage_location_id is not None:
        storage_stmt = select(StorageLocation).where(
            StorageLocation.id == inventory_data.storage_location_id,
            StorageLocation.kitchen_id == item.kitchen_id,
            )
        if db.scalar(storage_stmt) is None:
            raise ValueError("Storage location not found or does not belong to this kitchen.")

    # Update fields
    if inventory_data.food_item_id is not None:
        item.food_item_id = inventory_data.food_item_id
    if inventory_data.storage_location_id is not None:
        item.storage_location_id = inventory_data.storage_location_id
    if inventory_data.quantity is not None:
        item.quantity = inventory_data.quantity
    if inventory_data.min_quantity is not None:
        item.min_quantity = inventory_data.min_quantity
    if inventory_data.expiration_date is not None:
        item.expiration_date = inventory_data.expiration_date

    db.commit()
    db.refresh(item)
    return item


def delete_inventory_item(db: Session, inventory_id: int) -> None:
    """Remove an inventory item from the database.

    Args:
        db: Active database session.
        inventory_id: Primary key of the inventory item to delete.

    Raises:
        ValueError: If the inventory item does not exist.
    """
    item = get_inventory_item_by_id(db, inventory_id)
    if item is None:
        raise ValueError("Inventory item not found.")

    db.delete(item)
    db.commit()


def get_low_stock_items(db: Session, kitchen_id: int) -> list[InventoryItem]:
    """Return all inventory items that are below their minimum quantity.

    This function is designed to be used by AI services for automatic
    shopping list generation.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.

    Returns:
        A list of inventory items that are below their minimum quantity.

    Note:
        This function can be integrated with AI services to automatically
        generate shopping suggestions when items run low.
    """
    stmt = (
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item),
            selectinload(InventoryItem.storage_location),
        )
        .where(
            InventoryItem.kitchen_id == kitchen_id,
            InventoryItem.min_quantity.is_not(None),
            InventoryItem.quantity < InventoryItem.min_quantity,
            )
    )
    return list(db.scalars(stmt).all())


def get_expiring_items(
        db: Session, kitchen_id: int, days: int = 3
) -> list[InventoryItem]:
    """Return all inventory items that expire within the specified number of days.

    This function is designed to help with meal planning and waste reduction.

    Args:
        db: Database session.
        kitchen_id: Primary key of the kitchen.
        days: Number of days to look ahead (default: 3).

    Returns:
        A list of inventory items that expire within the specified timeframe.

    Note:
        This function can be integrated with AI services for meal planning
        to prioritize ingredients that are about to expire.
    """
    threshold_date = datetime.date.today() + datetime.timedelta(days=days)

    stmt = (
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item),
            selectinload(InventoryItem.storage_location),
        )
        .where(
            InventoryItem.kitchen_id == kitchen_id,
            InventoryItem.expiration_date.is_not(None),
            InventoryItem.expiration_date <= threshold_date,
            )
    )
    return list(db.scalars(stmt).all())