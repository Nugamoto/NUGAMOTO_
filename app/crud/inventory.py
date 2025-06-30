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
    StorageLocationRead,
    StorageLocationUpdate
)


# ================================================================== #
# Schema Conversion Helpers                                          #
# ================================================================== #

def build_inventory_item_read(item_orm: InventoryItem) -> InventoryItemRead:
    """Convert ORM to Read schema with computed properties.
    
    Public helper function that converts an InventoryItem ORM object
    to InventoryItemRead schema with all computed properties.
    
    Args:
        item_orm: InventoryItem ORM object with loaded relationships
        
    Returns:
        InventoryItemRead schema with computed properties
    """
    return InventoryItemRead(
        # Base fields from ORM
        id=item_orm.id,
        kitchen_id=item_orm.kitchen_id,
        food_item_id=item_orm.food_item_id,
        storage_location_id=item_orm.storage_location_id,
        quantity=item_orm.quantity,
        min_quantity=item_orm.min_quantity,
        expiration_date=item_orm.expiration_date,
        updated_at=item_orm.updated_at,
        
        # Related objects (loaded via selectinload)
        food_item=item_orm.food_item,
        storage_location=item_orm.storage_location,
        
        # Computed properties from ORM methods
        is_low_stock=item_orm.is_low_stock(),
        is_expired=item_orm.is_expired(),
        expires_soon=item_orm.expires_soon(),
        
        # Base unit name from relationship
        base_unit_name=item_orm.food_item.base_unit.name if item_orm.food_item.base_unit else 'units'
    )


def build_storage_location_read(storage_orm: StorageLocation) -> StorageLocationRead:
    """Convert StorageLocation ORM to Read schema.
    
    Args:
        storage_orm: StorageLocation ORM object
        
    Returns:
        StorageLocationRead schema
    """
    return StorageLocationRead(
        id=storage_orm.id,
        kitchen_id=storage_orm.kitchen_id,
        name=storage_orm.name
    )


# ================================================================== #
# StorageLocation CRUD Operations - Schema Returns                  #
# ================================================================== #

def create_storage_location(
        db: Session,
        kitchen_id: int,
        storage_data: StorageLocationCreate
) -> StorageLocationRead:
    """Create a new storage location for a kitchen.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        storage_data: Storage location creation data
        
    Returns:
        Created storage location schema
        
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

    return build_storage_location_read(db_storage)


def get_storage_location_by_id(
        db: Session,
        storage_location_id: int
) -> StorageLocationRead | None:
    """Get storage location by ID - returns schema.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to fetch
        
    Returns:
        Storage location schema or None if not found
    """
    storage_orm = db.scalar(
        select(StorageLocation)
        .where(StorageLocation.id == storage_location_id)
    )
    
    if not storage_orm:
        return None
    
    return build_storage_location_read(storage_orm)


def get_kitchen_storage_locations(
        db: Session,
        kitchen_id: int
) -> list[StorageLocationRead]:
    """Get all storage locations for a kitchen - returns schemas.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of storage location schemas
    """
    storage_orms = db.scalars(
        select(StorageLocation)
        .where(StorageLocation.kitchen_id == kitchen_id)
        .order_by(StorageLocation.name)
    ).all()
    
    return [build_storage_location_read(storage) for storage in storage_orms]


def update_storage_location(
        db: Session,
        storage_location_id: int,
        storage_data: StorageLocationUpdate
) -> StorageLocationRead | None:
    """Update an existing storage location.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to update
        storage_data: Updated storage location data
        
    Returns:
        Updated storage location schema or None if not found
    """
    # Get ORM object first
    db_storage = db.scalar(
        select(StorageLocation)
        .where(StorageLocation.id == storage_location_id)
    )
    
    if not db_storage:
        return None

    update_data = storage_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_storage, field, value)

    db.commit()
    db.refresh(db_storage)

    return build_storage_location_read(db_storage)


def delete_storage_location(db: Session, storage_location_id: int) -> bool:
    """Delete a storage location.
    
    Args:
        db: Database session
        storage_location_id: Storage location ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    db_storage = db.scalar(
        select(StorageLocation)
        .where(StorageLocation.id == storage_location_id)
    )
    
    if not db_storage:
        return False

    db.delete(db_storage)
    db.commit()

    return True


# ================================================================== #
# InventoryItem CRUD Operations - Schema Returns                    #
# ================================================================== #

def create_or_update_inventory_item(
        db: Session,
        kitchen_id: int,
        inventory_data: InventoryItemCreate
) -> InventoryItemRead:
    """Create a new inventory item or update existing one.
    
    If an inventory item for the same food item and storage location already
    exists, the quantities will be combined and other fields updated.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        inventory_data: Inventory item creation data
        
    Returns:
        Created or updated inventory item schema with computed properties
        
    Raises:
        ValueError: If food_item_id or storage_location_id don't exist
    """
    # Check if item already exists
    existing_item = db.scalar(
        select(InventoryItem)
        .options(selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit))
        .options(selectinload(InventoryItem.storage_location))
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

        existing_item.updated_at = datetime.datetime.now(datetime.timezone.utc)
        
        db.commit()
        db.refresh(existing_item)

        return build_inventory_item_read(existing_item)
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

        # Load relationships for schema conversion
        db_inventory = db.scalar(
            select(InventoryItem)
            .options(selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit))
            .options(selectinload(InventoryItem.storage_location))
            .where(InventoryItem.id == db_inventory.id)
        )

        return build_inventory_item_read(db_inventory)


def get_inventory_item_by_id(db: Session, inventory_item_id: int) -> InventoryItemRead | None:
    """Get inventory item by ID - returns schema.
    
    Args:
        db: Database session
        inventory_item_id: Inventory item ID to fetch
        
    Returns:
        Inventory item schema with computed properties or None if not found
    """
    item_orm = db.scalar(
        select(InventoryItem)
        .options(selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit))
        .options(selectinload(InventoryItem.storage_location))
        .where(InventoryItem.id == inventory_item_id)
    )
    
    if not item_orm:
        return None
    
    return build_inventory_item_read(item_orm)


def get_kitchen_inventory(db: Session, kitchen_id: int) -> list[InventoryItemRead]:
    """Get all inventory items for a kitchen - returns schemas.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of inventory item schemas with computed properties
    """
    items_orm = db.scalars(
        select(InventoryItem)
        .options(selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit))
        .options(selectinload(InventoryItem.storage_location))
        .where(InventoryItem.kitchen_id == kitchen_id)
    ).all()
    
    return [build_inventory_item_read(item) for item in items_orm]


def get_kitchen_inventory_grouped_by_storage(
        db: Session,
        kitchen_id: int
) -> dict[StorageLocationRead, list[InventoryItemRead]]:
    """Get kitchen inventory grouped by storage location - returns schemas.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        Dictionary mapping storage location schemas to their inventory item schemas
    """
    # Get all storage locations for the kitchen (as schemas)
    storage_locations = get_kitchen_storage_locations(db, kitchen_id)

    result = {}

    for storage_schema in storage_locations:
        # Get inventory items for this storage location
        items_orm = db.scalars(
            select(InventoryItem)
            .options(selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit))
            .options(selectinload(InventoryItem.storage_location))
            .where(
                and_(
                    InventoryItem.kitchen_id == kitchen_id,
                    InventoryItem.storage_location_id == storage_schema.id
                )
            )
        ).all()
        
        items_schemas = [build_inventory_item_read(item) for item in items_orm]
        result[storage_schema] = items_schemas

    return result


def update_inventory_item(
        db: Session,
        inventory_item_id: int,
        inventory_data: InventoryItemUpdate
) -> InventoryItemRead | None:
    """Update an existing inventory item.
    
    Args:
        db: Database session
        inventory_item_id: Inventory item ID to update
        inventory_data: Updated inventory item data
        
    Returns:
        Updated inventory item schema with computed properties or None if not found
    """
    # Get the ORM object first  
    db_inventory = db.scalar(
        select(InventoryItem)
        .options(selectinload(InventoryItem.food_item).selectinload(FoodItem.base_unit))
        .options(selectinload(InventoryItem.storage_location))
        .where(InventoryItem.id == inventory_item_id)
    )
    
    if not db_inventory:
        return None

    update_data = inventory_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_inventory, field, value)

    # Always update the timestamp
    db_inventory.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(db_inventory)

    return build_inventory_item_read(db_inventory)


def delete_inventory_item(db: Session, inventory_item_id: int) -> bool:
    """Delete an inventory item.
    
    Args:
        db: Database session
        inventory_item_id: Inventory item ID to delete
        
    Returns:
        True if deleted, False if not found
    """
    db_inventory = db.scalar(
        select(InventoryItem)
        .where(InventoryItem.id == inventory_item_id)
    )
    
    if not db_inventory:
        return False

    db.delete(db_inventory)
    db.commit()

    return True


# ================================================================== #
# Inventory Analysis Operations - Schema Returns                    #
# ================================================================== #

def get_low_stock_items(
        db: Session,
        kitchen_id: int
) -> list[InventoryItemRead]:
    """Get all inventory items that are below their minimum quantity threshold.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of low-stock inventory item schemas with computed properties
    """
    items_orm = db.scalars(
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
    ).all()
    
    return [build_inventory_item_read(item) for item in items_orm]


def get_expiring_items(
        db: Session,
        kitchen_id: int,
        threshold_days: int = EXPIRING_ITEMS_THRESHOLD_DAYS
) -> list[InventoryItemRead]:
    """Get all inventory items that expire within the specified threshold.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        threshold_days: Number of days to consider as "expiring soon"
        
    Returns:
        List of expiring inventory item schemas with computed properties
    """
    threshold_date = datetime.date.today() + datetime.timedelta(days=threshold_days)

    items_orm = db.scalars(
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
    ).all()
    
    return [build_inventory_item_read(item) for item in items_orm]


def get_expired_items(db: Session, kitchen_id: int) -> list[InventoryItemRead]:
    """Get all inventory items that have already expired.
    
    Args:
        db: Database session
        kitchen_id: Kitchen ID
        
    Returns:
        List of expired inventory item schemas with computed properties
    """
    today = datetime.date.today()

    items_orm = db.scalars(
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
    ).all()
    
    return [build_inventory_item_read(item) for item in items_orm]


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