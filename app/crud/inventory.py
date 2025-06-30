"""CRUD operations for inventory management."""

from __future__ import annotations

import datetime

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.models.food import FoodItem
from app.models.inventory import (
    EXPIRING_ITEMS_THRESHOLD_DAYS,
    InventoryItem,
    StorageLocation
)
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    StorageLocationCreate,
    StorageLocationUpdate
)


# ================================================================== #
# StorageLocation CRUD Operations                                    #
# ================================================================== #

def create_storage_location(
        db: Session,
        kitchen_id: int,
        storage_data: StorageLocationCreate
) -> StorageLocation:
    """Create a new storage location for a kitchen.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        storage_data: Storage location creation data
        
    Returns:
        Created storage location instance
        
    Raises:
        IntegrityError: If storage location name already exists in kitchen
    """
    db_storage = StorageLocation(
        kitchen_id=kitchen_id,
        name=storage_data.name
    )

    db.add(db_storage)
    db.commit()
    db.refresh(db_storage)

    return db_storage


def get_storage_location_by_id(
        db: Session,
        storage_location_id: int
) -> StorageLocation | None:
    """Get storage location by ID.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to fetch
        
    Returns:
        Storage location instance or None if not found
    """
    return db.scalar(
        select(StorageLocation)
        .where(StorageLocation.id == storage_location_id)
    )


def get_kitchen_storage_locations(
        db: Session,
        kitchen_id: int
) -> list[StorageLocation]:
    """Get all storage locations for a kitchen.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of storage location instances
    """
    return list(db.scalars(
        select(StorageLocation)
        .where(StorageLocation.kitchen_id == kitchen_id)
        .order_by(StorageLocation.name)
    ).all())


def update_storage_location(
        db: Session,
        storage_location_id: int,
        storage_data: StorageLocationUpdate
) -> StorageLocation | None:
    """Update an existing storage location.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to update
        storage_data: Updated storage location data
        
    Returns:
        Updated storage location instance or None if not found
    """
    db_storage = get_storage_location_by_id(db, storage_location_id)
    if not db_storage:
        return None

    update_data = storage_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_storage, field, value)

    db.commit()
    db.refresh(db_storage)

    return db_storage


def delete_storage_location(db: Session, storage_location_id: int) -> bool:
    """Delete a storage location.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    db_storage = get_storage_location_by_id(db, storage_location_id)
    if not db_storage:
        return False

    db.delete(db_storage)
    db.commit()

    return True


# ================================================================== #
# InventoryItem CRUD Operations                                      #
# ================================================================== #

def create_or_update_inventory_item(
        db: Session,
        kitchen_id: int,
        inventory_data: InventoryItemCreate
) -> InventoryItem:
    """Create a new inventory item or update existing one.
    
    If an inventory item for the same food item and storage location already
    exists, the quantities will be combined and other fields updated.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        inventory_data: Inventory item creation data
        
    Returns:
        Created or updated inventory item instance
        
    Raises:
        ValueError: If food_item_id or storage_location_id don't exist
    """
    # Check if item already exists
    existing_item = db.scalar(
        select(InventoryItem)
        .where(
            and_(
                InventoryItem.kitchen_id == kitchen_id,
                InventoryItem.food_item_id == inventory_data.food_item_id,
                InventoryItem.storage_location_id == inventory_data.storage_location_id
            )
        )
    )

    if existing_item:
        # Update existing item - combine quantities
        existing_item.quantity += inventory_data.quantity

        # Update other fields if provided
        if inventory_data.min_quantity is not None:
            existing_item.min_quantity = inventory_data.min_quantity
        if inventory_data.expiration_date is not None:
            existing_item.expiration_date = inventory_data.expiration_date

        existing_item.last_updated = datetime.datetime.now(datetime.timezone.utc)
        
        db.commit()
        db.refresh(existing_item)

        return existing_item
    else:
        # Create new item
        db_inventory = InventoryItem(
            kitchen_id=kitchen_id,
            food_item_id=inventory_data.food_item_id,
            storage_location_id=inventory_data.storage_location_id,
            quantity=inventory_data.quantity,
            min_quantity=inventory_data.min_quantity,
            expiration_date=inventory_data.expiration_date
        )

        db.add(db_inventory)
        db.commit()
        db.refresh(db_inventory)

        return db_inventory


def get_inventory_item_by_id(db: Session, inventory_item_id: int) -> InventoryItem | None:
    """Get inventory item by ID with related data.
    
    Args:
        db: Database session
        inventory_item_id: Inventory item ID to fetch
        
    Returns:
        Inventory item instance with related data or None if not found
    """
    return db.scalar(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit),
            selectinload(InventoryItem.storage_location)
        )
        .where(InventoryItem.id == inventory_item_id)
    )


def get_kitchen_inventory(
        db: Session,
        kitchen_id: int,
        food_item_id: int | None = None,
        storage_location_id: int | None = None
) -> list[InventoryItem]:
    """Get inventory items for a kitchen with optional filtering.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        food_item_id: Optional food item filter
        storage_location_id: Optional storage location filter
        
    Returns:
        List of inventory item instances with related data
    """
    query = (
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit),
            selectinload(InventoryItem.storage_location)
        )
        .where(InventoryItem.kitchen_id == kitchen_id)
        .order_by(InventoryItem.food_item_id, InventoryItem.storage_location_id)
    )

    if food_item_id is not None:
        query = query.where(InventoryItem.food_item_id == food_item_id)

    if storage_location_id is not None:
        query = query.where(InventoryItem.storage_location_id == storage_location_id)
    
    return list(db.scalars(query).all())


def get_kitchen_inventory_grouped_by_storage(
        db: Session,
        kitchen_id: int
) -> dict[StorageLocation, list[InventoryItem]]:
    """Get kitchen inventory grouped by storage location.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        Dictionary mapping storage locations to their inventory items
    """
    # Get all storage locations for the kitchen
    storage_locations = get_kitchen_storage_locations(db, kitchen_id)

    result = {}

    for storage in storage_locations:
        # Get inventory items for this storage location
        items = get_kitchen_inventory(
            db=db,
            kitchen_id=kitchen_id,
            storage_location_id=storage.id
        )
        result[storage] = items

    return result


def update_inventory_item(
        db: Session,
        inventory_item_id: int,
        inventory_data: InventoryItemUpdate
) -> InventoryItem | None:
    """Update an existing inventory item.
    
    Args:
        db: Database session
        inventory_item_id: Inventory item ID to update
        inventory_data: Updated inventory item data
        
    Returns:
        Updated inventory item instance or None if not found
    """
    db_inventory = get_inventory_item_by_id(db, inventory_item_id)
    if not db_inventory:
        return None

    update_data = inventory_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_inventory, field, value)

    # Always update the timestamp
    db_inventory.last_updated = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(db_inventory)

    return db_inventory


def delete_inventory_item(db: Session, inventory_item_id: int) -> bool:
    """Delete an inventory item.
    
    Args:
        db: Database session
        inventory_item_id: Inventory item ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    db_inventory = get_inventory_item_by_id(db, inventory_item_id)
    if not db_inventory:
        return False

    db.delete(db_inventory)
    db.commit()

    return True


# ================================================================== #
# Inventory Analysis Operations                                      #
# ================================================================== #

def get_low_stock_items(
        db: Session,
        kitchen_id: int
) -> list[InventoryItem]:
    """Get all inventory items that are below their minimum quantity threshold.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of low-stock inventory items with related data
    """
    return list(db.scalars(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit),
            selectinload(InventoryItem.storage_location)
        )
        .where(
            and_(
                InventoryItem.kitchen_id == kitchen_id,
                InventoryItem.min_quantity.is_not(None),
                InventoryItem.quantity < InventoryItem.min_quantity
            )
        )
        .order_by(InventoryItem.food_item_id)
    ).all())


def get_expiring_items(
        db: Session,
        kitchen_id: int,
        threshold_days: int = EXPIRING_ITEMS_THRESHOLD_DAYS
) -> list[InventoryItem]:
    """Get all inventory items that expire within the specified threshold.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        threshold_days: Number of days to consider as "expiring soon"
        
    Returns:
        List of expiring inventory items with related data, ordered by expiration date
    """
    threshold_date = datetime.date.today() + datetime.timedelta(days=threshold_days)

    return list(db.scalars(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit),
            selectinload(InventoryItem.storage_location)
        )
        .where(
            and_(
                InventoryItem.kitchen_id == kitchen_id,
                InventoryItem.expiration_date.is_not(None),
                InventoryItem.expiration_date <= threshold_date
            )
        )
        .order_by(InventoryItem.expiration_date)
    ).all())


def get_expired_items(db: Session, kitchen_id: int) -> list[InventoryItem]:
    """Get all inventory items that have already expired.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of expired inventory items with related data
    """
    today = datetime.date.today()

    return list(db.scalars(
        select(InventoryItem)
        .options(
            selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit),
            selectinload(InventoryItem.storage_location)
        )
        .where(
            and_(
                InventoryItem.kitchen_id == kitchen_id,
                InventoryItem.expiration_date.is_not(None),
                InventoryItem.expiration_date < today
            )
        )
        .order_by(InventoryItem.expiration_date)
    ).all())


# ================================================================== #
# Unit Conversion Helper (Future)                                    #
# ================================================================== #

def convert_quantity_to_base_unit(
        db: Session,
        food_item_id: int,
        quantity: float,
        input_unit_id: int
) -> float:
    """Convert a quantity from input unit to the food item's base unit.
    
    Conversion priority:
    1. If input unit equals base unit, return quantity unchanged
    2. Look for food-specific conversions in food_item_unit_conversions
    3. Fallback to generic unit conversions
    4. Raise ValueError if no conversion path exists
    
    Args:
        db: Database session
        food_item_id: Food item ID
        quantity: Quantity in input unit
        input_unit_id: Input unit ID
        
    Returns:
        Quantity converted to base unit
        
    Raises:
        ValueError: If food item not found or no conversion path exists
    """
    # Import here to avoid circular imports
    from app.crud import food as crud_food
    from app.crud import core as crud_core

    # 1. Get the food item with base_unit_id
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise ValueError(f"Food item with ID {food_item_id} not found")

    base_unit_id = food_item.base_unit_id

    # 2. If input unit equals base unit, return quantity unchanged
    if input_unit_id == base_unit_id:
        return quantity

    # 3. Check food-specific conversions first (higher priority)
    food_conversion_factor = crud_food.get_conversion_factor_for_food_item(
        db=db,
        food_item_id=food_item_id,
        from_unit_id=input_unit_id,
        to_unit_id=base_unit_id
    )

    if food_conversion_factor is not None:
        return quantity * food_conversion_factor

    # 4. Fallback to generic unit conversions
    generic_conversion_factor = crud_core.get_conversion_factor(
        db=db,
        from_unit_id=input_unit_id,
        to_unit_id=base_unit_id
    )

    if generic_conversion_factor is not None:
        return quantity * generic_conversion_factor

    # 5. No conversion path found
    # Get unit names for better error message
    input_unit = crud_core.get_unit_by_id(db=db, unit_id=input_unit_id)
    base_unit = crud_core.get_unit_by_id(db=db, unit_id=base_unit_id)

    input_unit_name = input_unit.name if input_unit else f"ID {input_unit_id}"
    base_unit_name = base_unit.name if base_unit else f"ID {base_unit_id}"

    raise ValueError(
        f"No conversion path found from '{input_unit_name}' to '{base_unit_name}' "
        f"for food item '{food_item.name}' (ID {food_item_id})"
    )


def _get_food_specific_conversion_factor(
        db: Session,
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> float | None:
    """Get food-specific conversion factor.
    
    Internal helper function to check food_item_unit_conversions table.
    
    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID
        
    Returns:
        Conversion factor or None if not found
    """
    from app.models.food import FoodItemUnitConversion

    conversion = db.scalar(
        select(FoodItemUnitConversion.factor)
        .where(
            and_(
                FoodItemUnitConversion.food_item_id == food_item_id,
                FoodItemUnitConversion.from_unit_id == from_unit_id,
                FoodItemUnitConversion.to_unit_id == to_unit_id
            )
        )
    )

    return conversion


def _get_generic_conversion_factor(
        db: Session,
        from_unit_id: int,
        to_unit_id: int
) -> float | None:
    """Get generic conversion factor between units.
    
    Internal helper function to check unit_conversions table.
    
    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID
        
    Returns:
        Conversion factor or None if not found
    """
    from app.models.core import UnitConversion

    conversion = db.scalar(
        select(UnitConversion.factor)
        .where(
            and_(
                UnitConversion.from_unit_id == from_unit_id,
                UnitConversion.to_unit_id == to_unit_id
            )
        )
    )

    return conversion


def _build_inventory_item_read(item_orm: InventoryItem) -> InventoryItemRead:
    """Convert ORM to Read schema with computed properties."""
    return InventoryItemRead(
        # Base fields (automatic via from_attributes=True)
        **{k: v for k, v in item_orm.__dict__.items() if not k.startswith('_')},

        # Related objects
        food_item=item_orm.food_item,
        storage_location=item_orm.storage_location,

        # Computed properties
        is_low_stock=item_orm.is_low_stock(),
        is_expired=item_orm.is_expired(),
        expires_soon=item_orm.expires_soon(),

        # Base unit name from relationship
        base_unit_name=item_orm.food_item.base_unit.name if item_orm.food_item.base_unit else 'units'
    )
