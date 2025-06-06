"""CRUD operations for inventory management."""

from __future__ import annotations

import datetime

from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.inventory import FoodItem, StorageLocation, InventoryItem
from app.schemas.inventory import (
    FoodItemCreate, FoodItemUpdate,
    StorageLocationCreate, StorageLocationUpdate,
    InventoryItemCreate, InventoryItemUpdate,
    KitchenInventorySummary, StorageLocationWithInventory
)

# Import settings at module level
EXPIRING_ITEMS_THRESHOLD_DAYS = settings.expiring_items_threshold_days


# ------------------------------------------------------------------ #
# FoodItem CRUD                                                      #
# ------------------------------------------------------------------ #

def create_food_item(db: Session, food_item_data: FoodItemCreate) -> FoodItem:
    """Create a new food item.

    Args:
        db: Database session.
        food_item_data: Validated food item data.

    Returns:
        The newly created food item.

    Raises:
        ValueError: If base_unit_id does not exist.

    Example:
        >>> data = FoodItemCreate(
        ...     name="Tomato",
        ...     category="Vegetables",
        ...     base_unit_id=1  # grams
        ... )
        >>> result = create_food_item(db, data)
    """
    # TODO: Add validation that base_unit_id exists in units table
    # For now, we assume the base_unit_id is valid

    db_food_item = FoodItem(
        name=food_item_data.name,
        category=food_item_data.category,
        base_unit_id=food_item_data.base_unit_id,
    )

    db.add(db_food_item)
    db.commit()
    db.refresh(db_food_item)

    return db_food_item


def get_food_item_by_id(db: Session, food_item_id: int) -> FoodItem | None:
    """Retrieve a food item by its ID.

    Args:
        db: Database session.
        food_item_id: The unique identifier of the food item.

    Returns:
        The food item if found, None otherwise.

    Example:
        >>> food_item = get_food_item_by_id(db, 123)
        >>> if food_item:
        ...     print(f"Found: {food_item.name} (base unit: {food_item.base_unit_id})")
    """
    return db.scalar(select(FoodItem).where(FoodItem.id == food_item_id))


def get_food_item_by_name(db: Session, name: str) -> FoodItem | None:
    """Retrieve a food item by its name (case-insensitive).

    Args:
        db: Database session.
        name: The name of the food item.

    Returns:
        The food item if found, None otherwise.
    """
    return db.scalar(select(FoodItem).where(FoodItem.name.ilike(name)))


def get_all_food_items(db: Session, skip: int = 0, limit: int = 100) -> list[FoodItem]:
    """Retrieve all food items with pagination.

    Args:
        db: Database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of food items ordered by name.
    """
    query = select(FoodItem).order_by(FoodItem.name).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def update_food_item(
        db: Session,
        food_item_id: int,
        food_item_data: FoodItemUpdate
) -> FoodItem | None:
    """Update an existing food item.

    Args:
        db: Database session.
        food_item_id: The unique identifier of the food item.
        food_item_data: Validated update data.

    Returns:
        The updated food item if found, None otherwise.

    Example:
        >>> data = FoodItemUpdate(name="Cherry Tomato", base_unit_id=2)
        >>> result = update_food_item(db, 123, data)
    """
    db_food_item = db.scalar(select(FoodItem).where(FoodItem.id == food_item_id))

    if db_food_item is None:
        return None

    # Update only provided fields
    update_data = food_item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_food_item, field, value)

    db.commit()
    db.refresh(db_food_item)

    return db_food_item


def delete_food_item(db: Session, food_item_id: int) -> bool:
    """Delete a food item by its ID.

    Args:
        db: Database session.
        food_item_id: The unique identifier of the food item.

    Returns:
        True if the food item was deleted, False if it wasn't found.

    Note:
        This will fail if the food item is referenced by inventory items
        due to foreign key constraints.
    """
    db_food_item = db.scalar(select(FoodItem).where(FoodItem.id == food_item_id))

    if db_food_item is None:
        return False

    db.delete(db_food_item)
    db.commit()
    return True


# ------------------------------------------------------------------ #
# StorageLocation CRUD                                               #
# ------------------------------------------------------------------ #

def create_storage_location(
        db: Session,
        kitchen_id: int,
        storage_data: StorageLocationCreate
) -> StorageLocation:
    """Create a new storage location for a kitchen.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen this storage location belongs to.
        storage_data: Validated storage location data.

    Returns:
        The newly created storage location.

    Example:
        >>> data = StorageLocationCreate(name="Refrigerator")
        >>> result = create_storage_location(db, 123, data)
    """
    db_storage = StorageLocation(
        kitchen_id=kitchen_id,
        name=storage_data.name,
    )

    db.add(db_storage)
    db.commit()
    db.refresh(db_storage)

    return db_storage


def get_storage_location_by_id(db: Session, storage_id: int) -> StorageLocation | None:
    """Retrieve a storage location by its ID.

    Args:
        db: Database session.
        storage_id: The unique identifier of the storage location.

    Returns:
        The storage location if found, None otherwise.
    """
    return db.scalar(select(StorageLocation).where(StorageLocation.id == storage_id))


def get_kitchen_storage_locations(
        db: Session,
        kitchen_id: int
) -> list[StorageLocation]:
    """Retrieve all storage locations for a specific kitchen.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen.

    Returns:
        A list of storage locations ordered by name.
    """
    query = (
        select(StorageLocation)
        .where(StorageLocation.kitchen_id == kitchen_id)
        .order_by(StorageLocation.name)
    )
    return list(db.scalars(query).all())


def update_storage_location(
        db: Session,
        storage_id: int,
        storage_data: StorageLocationUpdate
) -> StorageLocation | None:
    """Update an existing storage location.

    Args:
        db: Database session.
        storage_id: The unique identifier of the storage location.
        storage_data: Validated update data.

    Returns:
        The updated storage location if found, None otherwise.
    """
    db_storage = db.scalar(select(StorageLocation).where(StorageLocation.id == storage_id))

    if db_storage is None:
        return None

    # Update only provided fields
    update_data = storage_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_storage, field, value)

    db.commit()
    db.refresh(db_storage)

    return db_storage


def delete_storage_location(db: Session, storage_id: int) -> bool:
    """Delete a storage location by its ID.

    Args:
        db: Database session.
        storage_id: The unique identifier of the storage location.

    Returns:
        True if the storage location was deleted, False if it wasn't found.

    Note:
        This will fail if the storage location contains inventory items
        due to foreign key constraints.
    """
    db_storage = db.scalar(select(StorageLocation).where(StorageLocation.id == storage_id))

    if db_storage is None:
        return False

    db.delete(db_storage)
    db.commit()
    return True


# ------------------------------------------------------------------ #
# InventoryItem CRUD                                                 #
# ------------------------------------------------------------------ #

def create_or_update_inventory_item(
        db: Session,
        kitchen_id: int,
        inventory_data: InventoryItemCreate
) -> InventoryItem:
    """Create a new inventory item or update existing one if combination exists.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen.
        inventory_data: Validated inventory item data.

    Returns:
        The created or updated inventory item.

    Raises:
        ValueError: If food_item does not exist or has no base_unit_id.

    Example:
        >>> data = InventoryItemCreate(
        ...     food_item_id=1,
        ...     storage_location_id=2,
        ...     quantity=500.0,  # 500 grams (base unit)
        ...     min_quantity=100.0
        ... )
        >>> result = create_or_update_inventory_item(db, 123, data)
    """
    # Validate that food_item exists and has base_unit_id
    food_item = get_food_item_by_id(db, inventory_data.food_item_id)
    if food_item is None:
        raise ValueError(f"Food item with ID {inventory_data.food_item_id} not found")

    if food_item.base_unit_id is None:
        raise ValueError(f"Food item {food_item.name} has no base unit defined")

    # Check if inventory item already exists for this combination
    existing_item = db.scalar(
        select(InventoryItem).where(
            and_(
                InventoryItem.kitchen_id == kitchen_id,
                InventoryItem.food_item_id == inventory_data.food_item_id,
                InventoryItem.storage_location_id == inventory_data.storage_location_id
            )
        )
    )

    if existing_item:
        # Update existing item (add to existing quantity)
        existing_item.quantity += inventory_data.quantity
        if inventory_data.min_quantity is not None:
            existing_item.min_quantity = inventory_data.min_quantity
        if inventory_data.expiration_date is not None:
            existing_item.expiration_date = inventory_data.expiration_date
        existing_item.last_updated = datetime.datetime.now(datetime.timezone.utc)
        
        db.commit()
        db.refresh(existing_item)
        return existing_item
    else:
        # Create new inventory item
        # Note: Quantity is stored in base unit as provided
        db_inventory = InventoryItem(
            kitchen_id=kitchen_id,
            food_item_id=inventory_data.food_item_id,
            storage_location_id=inventory_data.storage_location_id,
            quantity=inventory_data.quantity,  # Already in base unit
            min_quantity=inventory_data.min_quantity,
            expiration_date=inventory_data.expiration_date,
            last_updated=datetime.datetime.now(datetime.timezone.utc),
        )

        db.add(db_inventory)
        db.commit()
        db.refresh(db_inventory)

        return db_inventory


def get_inventory_item_by_id(db: Session, inventory_id: int) -> InventoryItem | None:
    """Retrieve an inventory item by its ID with related objects.

    Args:
        db: Database session.
        inventory_id: The unique identifier of the inventory item.

    Returns:
        The inventory item with related food_item and storage_location if found.
    """
    return db.scalar(
        select(InventoryItem)
        .options(
            joinedload(InventoryItem.food_item),
            joinedload(InventoryItem.storage_location)
        )
        .where(InventoryItem.id == inventory_id)
    )


def get_kitchen_inventory(
        db: Session,
        kitchen_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[InventoryItem]:
    """Retrieve all inventory items for a specific kitchen.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of inventory items with related objects.
    """
    query = (
        select(InventoryItem)
        .options(
            joinedload(InventoryItem.food_item),
            joinedload(InventoryItem.storage_location)
        )
        .where(InventoryItem.kitchen_id == kitchen_id)
        .order_by(InventoryItem.food_item.has(FoodItem.name))
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(query).all())


def get_kitchen_inventory_grouped_by_storage(
        db: Session,
        kitchen_id: int
) -> KitchenInventorySummary:
    """Retrieve kitchen inventory grouped by storage location with summary stats.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen.

    Returns:
        Complete inventory summary with items grouped by storage location.
    """
    # Get all storage locations for the kitchen
    storage_locations = get_kitchen_storage_locations(db, kitchen_id)

    # Get all inventory items for the kitchen
    inventory_items = get_kitchen_inventory(db, kitchen_id, limit=1000)  # Large limit

    # Group items by storage location
    storage_with_inventory = []
    total_items = len(inventory_items)
    low_stock_items = 0
    expired_items = 0
    expires_soon_items = 0

    for storage_location in storage_locations:
        # Filter items for this storage location
        location_items = [
            item for item in inventory_items
            if item.storage_location_id == storage_location.id
        ]

        # Count items for summary
        for item in location_items:
            if item.is_low_stock:
                low_stock_items += 1
            if item.is_expired:
                expired_items += 1
            if item.expires_soon:
                expires_soon_items += 1

        storage_with_inventory.append(StorageLocationWithInventory(
            id=storage_location.id,
            kitchen_id=storage_location.kitchen_id,
            name=storage_location.name,
            inventory_items=location_items
        ))
    
    return KitchenInventorySummary(
        kitchen_id=kitchen_id,
        storage_locations=storage_with_inventory,
        total_items=total_items,
        low_stock_items=low_stock_items,
        expired_items=expired_items,
        expires_soon_items=expires_soon_items
    )


def update_inventory_item(
        db: Session,
        inventory_id: int,
        inventory_data: InventoryItemUpdate
) -> InventoryItem | None:
    """Update an existing inventory item.

    Args:
        db: Database session.
        inventory_id: The unique identifier of the inventory item.
        inventory_data: Validated update data.

    Returns:
        The updated inventory item if found, None otherwise.

    Note:
        When updating quantity, the new value should be in base units.
    """
    db_inventory = get_inventory_item_by_id(db, inventory_id)

    if db_inventory is None:
        return None

    # Validate food_item if being updated
    if inventory_data.food_item_id is not None:
        food_item = get_food_item_by_id(db, inventory_data.food_item_id)
        if food_item is None:
            raise ValueError(f"Food item with ID {inventory_data.food_item_id} not found")
        if food_item.base_unit_id is None:
            raise ValueError(f"Food item {food_item.name} has no base unit defined")

    # Update only provided fields
    update_data = inventory_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_inventory, field, value)

    # Update timestamp
    db_inventory.last_updated = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(db_inventory)

    return db_inventory


def delete_inventory_item(db: Session, inventory_id: int) -> bool:
    """Delete an inventory item by its ID.

    Args:
        db: Database session.
        inventory_id: The unique identifier of the inventory item.

    Returns:
        True if the inventory item was deleted, False if it wasn't found.
    """
    db_inventory = get_inventory_item_by_id(db, inventory_id)

    if db_inventory is None:
        return False

    db.delete(db_inventory)
    db.commit()
    return True


def get_low_stock_items(
        db: Session,
        kitchen_id: int
) -> list[InventoryItem]:
    """Retrieve all inventory items that are below their minimum quantity.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen.

    Returns:
        A list of inventory items that are low in stock.
    """
    query = (
        select(InventoryItem)
        .options(
            joinedload(InventoryItem.food_item),
            joinedload(InventoryItem.storage_location)
        )
        .where(
            and_(
                InventoryItem.kitchen_id == kitchen_id,
                InventoryItem.min_quantity.isnot(None),
                InventoryItem.quantity < InventoryItem.min_quantity
            )
        )
        .order_by(InventoryItem.food_item.has(FoodItem.name))
    )
    return list(db.scalars(query).all())


def get_expiring_items(
        db: Session,
        kitchen_id: int,
        days: int = EXPIRING_ITEMS_THRESHOLD_DAYS
) -> list[InventoryItem]:
    """Retrieve all inventory items that expire within the specified number of days.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen.
        days: Number of days to check ahead.

    Returns:
        A list of inventory items that expire soon or have already expired.
    """
    threshold_date = datetime.date.today() + datetime.timedelta(days=days)

    query = (
        select(InventoryItem)
        .options(
            joinedload(InventoryItem.food_item),
            joinedload(InventoryItem.storage_location)
        )
        .where(
            and_(
                InventoryItem.kitchen_id == kitchen_id,
                InventoryItem.expiration_date.isnot(None),
                InventoryItem.expiration_date <= threshold_date
            )
        )
        .order_by(InventoryItem.expiration_date)
    )
    return list(db.scalars(query).all())


# ------------------------------------------------------------------ #
# Unit Conversion Support (Future Implementation)                    #
# ------------------------------------------------------------------ #

def convert_quantity_to_base_unit(
        db: Session,
        food_item_id: int,
        quantity: float,
        from_unit_id: int
) -> float:
    """Convert quantity from specified unit to base unit.
    
    This function is a placeholder for future implementation when
    unit conversion tables are available.
    
    Args:
        db: Database session.
        food_item_id: ID of the food item.
        quantity: Quantity in the source unit.
        from_unit_id: ID of the source unit.
        
    Returns:
        Quantity converted to base unit.
        
    Note:
        Currently returns the original quantity unchanged.
        Future implementation will look up conversion factors from:
        - unit_conversions table (for standard unit conversions)
        - food_item_unit_conversions table (for food-specific conversions)
    """
    # TODO: Implement actual unit conversion logic
    # 1. Get food_item.base_unit_id
    # 2. Check if from_unit_id == base_unit_id (no conversion needed)
    # 3. Look up conversion factor in unit_conversions or food_item_unit_conversions
    # 4. Apply conversion: base_quantity = quantity * conversion_factor

    return quantity  # Placeholder - no conversion yet
