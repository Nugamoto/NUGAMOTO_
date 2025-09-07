"""CRUD operations for food system."""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from backend.crud.core import get_conversion_factor
from backend.models.food import FoodItem, FoodItemUnitConversion, FoodItemAlias
from backend.models.inventory import InventoryItem
from backend.schemas.food import (
    FoodItemCreate, FoodItemRead, FoodItemUpdate,
    FoodItemUnitConversionCreate, FoodItemUnitConversionRead,
    FoodItemAliasCreate, FoodItemAliasRead
)


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_food_item_read(food_orm: FoodItem) -> FoodItemRead:
    """Convert FoodItem ORM to Read schema.

    Args:
        food_orm: FoodItem ORM object with loaded relationships

    Returns:
        FoodItemRead schema
    """
    return FoodItemRead.model_validate(food_orm, from_attributes=True)


def build_food_item_alias_read(alias_orm: FoodItemAlias) -> FoodItemAliasRead:
    """Convert FoodItemAlias ORM to Read schema.

    Args:
        alias_orm: FoodItemAlias ORM object with loaded relationships

    Returns:
        FoodItemAliasRead schema
    """
    return FoodItemAliasRead.model_validate(alias_orm, from_attributes=True)


def build_food_item_unit_conversion_read(conversion_orm: FoodItemUnitConversion) -> FoodItemUnitConversionRead:
    """Convert FoodItemUnitConversion ORM to Read schema.

    Args:
        conversion_orm: FoodItemUnitConversion ORM object with loaded relationships

    Returns:
        FoodItemUnitConversionRead schema
    """
    return FoodItemUnitConversionRead.model_validate(conversion_orm, from_attributes=True)


# ================================================================== #
# FoodItem CRUD Operations - Schema Returns                         #
# ================================================================== #

def create_food_item(db: Session, food_item_data: FoodItemCreate) -> FoodItemRead:
    """Create a new food item - returns schema.

    Args:
        db: Database session
        food_item_data: Food item creation data

    Returns:
        Created food item schema

    Raises:
        IntegrityError: If food item name already exists or base_unit_id doesn't exist
    """
    db_food_item = FoodItem(
        name=food_item_data.name,
        category=food_item_data.category,
        base_unit_id=food_item_data.base_unit_id
    )

    db.add(db_food_item)
    db.commit()
    db.refresh(db_food_item)

    # Load relationships for schema conversion
    db_food_item = db.scalar(
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItem.id == db_food_item.id)
    )

    return build_food_item_read(db_food_item)


def get_food_item_by_id(db: Session, food_item_id: int) -> FoodItemRead | None:
    """Get food item by ID - returns schema.

    Args:
        db: Database session
        food_item_id: Food item ID to fetch

    Returns:
        Food item schema or None if not found
    """
    food_orm = db.scalar(
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItem.id == food_item_id)
    )

    if not food_orm:
        return None

    return build_food_item_read(food_orm)


def get_food_item_by_name(db: Session, food_item_name: str) -> FoodItemRead | None:
    """Get food item by name - returns schema.

    Args:
        db: Database session
        food_item_name: Food item name to search for

    Returns:
        Food item schema or None if not found
    """
    food_orm = db.scalar(
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItem.name == food_item_name.strip().title())
    )

    if not food_orm:
        return None

    return build_food_item_read(food_orm)


def get_all_food_items(
        db: Session,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[FoodItemRead]:
    """Get all food items with optional filtering - returns schemas.

    Args:
        db: Database session
        category: Optional category filter
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of food item schemas
    """
    query = (
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .order_by(FoodItem.category, FoodItem.name)
        .offset(skip)
        .limit(limit)
    )

    if category:
        query = query.where(FoodItem.category == category.strip().title())

    food_orms = db.scalars(query).all()

    return [build_food_item_read(food) for food in food_orms]


def get_food_items_by_category(db: Session, category: str) -> list[FoodItemRead]:
    """Get all food items in a specific category - returns schemas.

    Args:
        db: Database session
        category: Category to filter by

    Returns:
        List of food item schemas in the specified category
    """
    food_orms = db.scalars(
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItem.category == category.strip().title())
        .order_by(FoodItem.name)
    ).all()

    return [build_food_item_read(food) for food in food_orms]


def update_food_item(
        db: Session,
        food_item_id: int,
        food_item_data: FoodItemUpdate
) -> FoodItemRead | None:
    """Update an existing food item - returns schema.

    Args:
        db: Database session
        food_item_id: Food item ID to update
        food_item_data: Updated food item data

    Returns:
        Updated food item schema or None if not found
    """
    # Get ORM object first
    db_food_item = db.scalar(
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItem.id == food_item_id)
    )
    
    if not db_food_item:
        return None

    update_data = food_item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_food_item, field, value)

    db.commit()
    db.refresh(db_food_item)

    return build_food_item_read(db_food_item)


def delete_food_item(db: Session, food_item_id: int) -> bool:
    """Delete a food item.

    Will refuse deletion if the food item is currently referenced by any
    inventory items to avoid breaking NOT NULL constraints.

    Args:
        db: Database session
        food_item_id: Food item ID to delete

    Returns:
        True if deleted, False if not found

    Raises:
        ValueError: If inventory items reference this food item.
    """
    db_food_item = db.scalar(
        select(FoodItem).where(FoodItem.id == food_item_id)
    )
    if not db_food_item:
        return False

    has_refs = db.scalar(
        select(InventoryItem.id).where(InventoryItem.food_item_id == food_item_id).limit(1)
    )
    if has_refs is not None:
        raise ValueError(
            "Cannot delete this food item because it is used in inventory. "
            "Remove or reassign related inventory items first."
        )

    db.delete(db_food_item)
    db.commit()
    return True


# ================================================================== #
# FoodItemAlias CRUD Operations - Schema Returns                    #
# ================================================================== #

def create_food_item_alias(
        db: Session,
        alias_data: FoodItemAliasCreate
) -> FoodItemAliasRead:
    """Create a new food item alias - returns schema.

    Args:
        db: Database session
        alias_data: Alias creation data

    Returns:
        Created alias schema

    Raises:
        IntegrityError: If alias already exists for the combination of food_item_id, alias, and user_id
    """
    db_alias = FoodItemAlias(
        food_item_id=alias_data.food_item_id,
        alias=alias_data.alias,
        user_id=alias_data.user_id
    )

    db.add(db_alias)
    db.commit()
    db.refresh(db_alias)

    # Load relationships for schema conversion
    db_alias = db.scalar(
        select(FoodItemAlias)
        .options(
            selectinload(FoodItemAlias.food_item),
            selectinload(FoodItemAlias.user)
        )
        .where(FoodItemAlias.id == db_alias.id)
    )

    return build_food_item_alias_read(db_alias)


def get_aliases_for_food_item(
        db: Session,
        food_item_id: int,
        user_id: int | None = None
) -> list[FoodItemAliasRead]:
    """Get all aliases for a specific food item - returns schemas.

    Args:
        db: Database session
        food_item_id: Food item ID
        user_id: Optional user ID to filter user-specific aliases

    Returns:
        List of alias schemas for the food item
    """
    query = (
        select(FoodItemAlias)
        .options(
            selectinload(FoodItemAlias.food_item),
            selectinload(FoodItemAlias.user)
        )
        .where(FoodItemAlias.food_item_id == food_item_id)
        .order_by(FoodItemAlias.alias)
    )

    if user_id is not None:
        # Include global aliases (user_id is NULL) and user-specific aliases
        query = query.where(
            (FoodItemAlias.user_id == user_id) | (FoodItemAlias.user_id.is_(None))
        )

    alias_orms = db.scalars(query).all()

    return [build_food_item_alias_read(alias) for alias in alias_orms]


def get_all_aliases_for_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[FoodItemAliasRead]:
    """Get all aliases created by a specific user - returns schemas.

    Args:
        db: Database session
        user_id: User ID
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of alias schemas created by the user
    """
    alias_orms = db.scalars(
        select(FoodItemAlias)
        .options(
            selectinload(FoodItemAlias.food_item),
            selectinload(FoodItemAlias.user)
        )
        .where(FoodItemAlias.user_id == user_id)
        .order_by(FoodItemAlias.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    return [build_food_item_alias_read(alias) for alias in alias_orms]


def get_alias_by_id(db: Session, alias_id: int) -> FoodItemAliasRead | None:
    """Get alias by ID - returns schema.

    Args:
        db: Database session
        alias_id: Alias ID to fetch

    Returns:
        Alias schema or None if not found
    """
    alias_orm = db.scalar(
        select(FoodItemAlias)
        .options(
            selectinload(FoodItemAlias.food_item),
            selectinload(FoodItemAlias.user)
        )
        .where(FoodItemAlias.id == alias_id)
    )

    if not alias_orm:
        return None

    return build_food_item_alias_read(alias_orm)


def delete_alias_by_id(db: Session, alias_id: int) -> bool:
    """Delete an alias by ID.

    Args:
        db: Database session
        alias_id: Alias ID to delete

    Returns:
        True if deleted, False if not found
    """
    db_alias = db.scalar(
        select(FoodItemAlias)
        .where(FoodItemAlias.id == alias_id)
    )
    
    if not db_alias:
        return False

    db.delete(db_alias)
    db.commit()

    return True


def search_food_items_by_alias(
        db: Session,
        alias_term: str,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[FoodItemRead]:
    """Search food items by alias term - returns schemas.

    Args:
        db: Database session
        alias_term: Term to search for in aliases
        user_id: Optional user ID to include user-specific aliases
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of food item schemas that have matching aliases
    """
    query = (
        select(FoodItem)
        .join(FoodItemAlias)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItemAlias.alias.ilike(f"%{alias_term.strip()}%"))
        .distinct()
        .order_by(FoodItem.name)
        .offset(skip)
        .limit(limit)
    )

    if user_id is not None:
        # Include global aliases (user_id is NULL) and user-specific aliases
        query = query.where(
            (FoodItemAlias.user_id == user_id) | (FoodItemAlias.user_id.is_(None))
        )

    food_orms = db.scalars(query).all()

    return [build_food_item_read(food) for food in food_orms]


# ================================================================== #
# FoodItemUnitConversion CRUD Operations - Schema Returns           #
# ================================================================== #

def create_food_unit_conversion(
        db: Session,
        conversion_data: FoodItemUnitConversionCreate
) -> FoodItemUnitConversionRead:
    """Create a new food item unit conversion - returns schema.

    Args:
        db: Database session
        conversion_data: Unit conversion creation data

    Returns:
        Created unit conversion schema

    Raises:
        IntegrityError: If conversion already exists or referenced entities don't exist
    """
    db_conversion = FoodItemUnitConversion(
        food_item_id=conversion_data.food_item_id,
        from_unit_id=conversion_data.from_unit_id,
        to_unit_id=conversion_data.to_unit_id,
        factor=conversion_data.factor
    )

    db.add(db_conversion)
    db.commit()
    db.refresh(db_conversion)

    # Load relationships for schema conversion
    db_conversion = db.scalar(
        select(FoodItemUnitConversion)
        .options(
            selectinload(FoodItemUnitConversion.food_item),
            selectinload(FoodItemUnitConversion.from_unit),
            selectinload(FoodItemUnitConversion.to_unit)
        )
        .where(
            and_(
                FoodItemUnitConversion.food_item_id == db_conversion.food_item_id,
                FoodItemUnitConversion.from_unit_id == db_conversion.from_unit_id,
                FoodItemUnitConversion.to_unit_id == db_conversion.to_unit_id
            )
        )
    )

    return build_food_item_unit_conversion_read(db_conversion)


def get_food_unit_conversion(
        db: Session,
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> FoodItemUnitConversionRead | None:
    """Get specific food item unit conversion - returns schema.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Unit conversion schema or None if not found
    """
    conversion_orm = db.scalar(
        select(FoodItemUnitConversion)
        .options(
            selectinload(FoodItemUnitConversion.food_item),
            selectinload(FoodItemUnitConversion.from_unit),
            selectinload(FoodItemUnitConversion.to_unit)
        )
        .where(
            and_(
                FoodItemUnitConversion.food_item_id == food_item_id,
                FoodItemUnitConversion.from_unit_id == from_unit_id,
                FoodItemUnitConversion.to_unit_id == to_unit_id
            )
        )
    )

    if not conversion_orm:
        return None

    return build_food_item_unit_conversion_read(conversion_orm)


def get_conversion_factor_for_food_item(
        db: Session,
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> float | None:
    """Get the conversion factor for a specific food item, auto-handling reciprocals.

    This function attempts in order:
      1. Direct lookup in `food_item_unit_conversions` (from_unit_id → to_unit_id).
      2. Reciprocal lookup (to_unit_id → from_unit_id) and returns 1/factor.
      3. Returns None if no food-specific conversion exists.

    Args:
        db (Session): Database session.
        food_item_id (int): ID of the food item.
        from_unit_id (int): Source unit ID.
        to_unit_id (int): Target unit ID.

    Returns:
        float | None: Conversion factor such that
        `value * factor = converted_value`, or None if not found.

    Examples:
        >>> # Direct food-specific conversion exists
        >>> # e.g., for flour: 1 EL → 10 g
        >>> get_conversion_factor_for_food_item(db, food_item_id, from_unit_id, to_unit_id)
        10.0

        >>> # Reciprocal lookup: 10 g → 1 EL
        >>> get_conversion_factor_for_food_item(db, food_item_id, from_unit_id, to_unit_id)
        0.1
    """
    # 1) direct lookup - use the schema-returning function but extract the factor
    conv_schema = get_food_unit_conversion(db, food_item_id, from_unit_id, to_unit_id)
    if conv_schema:
        return conv_schema.factor

    # 2) reciprocal lookup
    rev_schema = get_food_unit_conversion(db, food_item_id, to_unit_id, from_unit_id)
    if rev_schema and rev_schema.factor != 0:
        return 1.0 / rev_schema.factor

    return None


def get_conversions_for_food_item(
        db: Session,
        food_item_id: int
) -> list[FoodItemUnitConversionRead]:
    """Get all unit conversions for a specific food item - returns schemas.

    Args:
        db: Database session
        food_item_id: Food item ID

    Returns:
        List of unit conversion schemas
    """
    conversion_orms = db.scalars(
        select(FoodItemUnitConversion)
        .options(
            selectinload(FoodItemUnitConversion.food_item),
            selectinload(FoodItemUnitConversion.from_unit),
            selectinload(FoodItemUnitConversion.to_unit)
        )
        .where(FoodItemUnitConversion.food_item_id == food_item_id)
        .where(FoodItemUnitConversion.from_unit_id != FoodItemUnitConversion.to_unit_id)  # ← FILTER HINZUGEFÜGT
        .order_by(FoodItemUnitConversion.from_unit_id, FoodItemUnitConversion.to_unit_id)
    ).all()

    return [build_food_item_unit_conversion_read(conv) for conv in conversion_orms]


def delete_food_unit_conversion(
        db: Session,
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> bool:
    """Delete a food item unit conversion.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        True if deleted, False if not found
    """
    conversion_orm = db.scalar(
        select(FoodItemUnitConversion)
        .where(
            and_(
                FoodItemUnitConversion.food_item_id == food_item_id,
                FoodItemUnitConversion.from_unit_id == from_unit_id,
                FoodItemUnitConversion.to_unit_id == to_unit_id
            )
        )
    )

    if not conversion_orm:
        return False

    db.delete(conversion_orm)
    db.commit()

    return True


# ================================================================== #
# Conversion Calculation Helper                                      #
# ================================================================== #

def convert_food_value(
        db: Session,
        food_item_id: int,
        value: float,
        from_unit_id: int,
        to_unit_id: int
) -> tuple[float, bool] | None:
    """Convert a quantity for a specific food item between units, with fallback.

    This function attempts in order:
      1. Food-specific conversion (via get_conversion_for_food_item).
      2. Generic conversion (via get_conversion_factor from core).
      3. Returns None if neither path exists.

    Args:
        db (Session): Database session.
        food_item_id (int): ID of the food item.
        value (float): Quantity in the source unit.
        from_unit_id (int): Source unit ID.
        to_unit_id (int): Target unit ID.

    Returns:
        tuple[float, bool] | None:
          - converted_value: The resulting quantity in the target unit.
          - is_food_specific: True if a food-specific conversion was used.
        Or None if no conversion path is found.

    Examples:
        >>> # Flour: 2 EL → g
        >>> convert_food_value(db, food_item_id, 2.0, from_unit_id, to_unit_id)
        (20.0, True)

        >>> # Flour: 20 g → EL (reciprocal)
        >>> convert_food_value(db, food_item_id, 20.0, from_unit_id, to_unit_id)
        (2.0, True)

        >>> # Generic weight conversion: 1 lb → kg
        >>> convert_food_value(db, food_item_id, 1.0, from_unit_id, to_unit_id)
        (0.453592, False)
    """
    if from_unit_id == to_unit_id:
        return value, False

    # 1) Try food-specific conversion (direct or reciprocal)
    factor = get_conversion_factor_for_food_item(db, food_item_id, from_unit_id, to_unit_id)
    if factor is not None:
        return value * factor, True

    # 2) Fall back to generic conversion for weight/volume
    factor = get_conversion_factor(db, from_unit_id, to_unit_id)
    if factor is not None:
        return value * factor, False

    return None


def can_convert_food_units(
        db: Session,
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> bool:
    """Determine whether two units can be converted for a given food item.

    This function attempts in order:
      1. Trivially true if source and target units are identical.
      2. Food-specific conversion (direct or reciprocal).
      3. Generic conversion for weight/volume via core.get_conversion_factor.

    Args:
        db (Session): The SQLAlchemy database session.
        food_item_id (int): The ID of the food item.
        from_unit_id (int): The source unit ID.
        to_unit_id (int): The target unit ID.

    Returns:
        bool: True if any conversion path exists, False otherwise.

    Examples:
        # Same unit
        assert can_convert_food_units(db, flour_id, g_id, g_id) is True

        # Food-specific conversion exists (e.g., EL ↔ g for flour)
        assert can_convert_food_units(db, flour_id, el_id, g_id) is True
        assert can_convert_food_units(db, flour_id, g_id, el_id) is True

        # Generic weight conversion (e.g., lb ↔ kg)
        assert can_convert_food_units(db, any_id, lb_id, kg_id) is True

        # No path between count and volume
        assert can_convert_food_units(db, any_id, piece_id, ml_id) is False
    """
    # 1) identical units
    if from_unit_id == to_unit_id:
        return True

    # 2) food-specific conversion (direct or reciprocal)
    if get_conversion_factor_for_food_item(db, food_item_id, from_unit_id, to_unit_id) is not None:
        return True

    # 3) generic conversion for weight/volume
    # Use get_conversion_factor which includes type checking and to_base_factor fallback
    if get_conversion_factor(db, from_unit_id, to_unit_id) is not None:
        return True

    # No conversion path found
    return False


# ================================================================== #
# Unit Conversion Utilities                                          #
# ================================================================== #

def convert_to_base_unit(
        db: Session,
        food_item_id: int,
        amount: float,
        from_unit_id: int
) -> float:
    """Convert amount to base unit for a food item - CRUD layer.

    Args:
        db: Database session
        food_item_id: ID of the food item
        amount: Amount to convert
        from_unit_id: Source unit ID

    Returns:
        Amount in base unit

    Raises:
        ValueError: If food item not found or conversion not possible
    """

    # Get food item
    food_item = db.scalar(select(FoodItem).where(FoodItem.id == food_item_id))
    if not food_item:
        raise ValueError(f"Food item {food_item_id} not found")

    # If already in base unit, return as-is
    if from_unit_id == food_item.base_unit_id:
        return amount

    # Try existing convert_food_value function
    result = convert_food_value(
        db=db,
        food_item_id=food_item_id,
        value=amount,
        from_unit_id=from_unit_id,
        to_unit_id=food_item.base_unit_id
    )

    if result and result[0] is not None:
        return result[0]  # Return converted value

    raise ValueError(
        f"Cannot convert from unit {from_unit_id} to base unit {food_item.base_unit_id} "
        f"for food item {food_item_id}"
    )


def get_available_units_for_food_item(db: Session, food_item_id: int) -> list[tuple[int, str]]:
    """Get all available units for a food item - CRUD layer.

    Args:
        db: Database session
        food_item_id: ID of the food item

    Returns:
        List of (unit_id, unit_name) tuples
    """

    food_item = db.scalar(
        select(FoodItem)
        .options(
            selectinload(FoodItem.base_unit),
            selectinload(FoodItem.unit_conversions).selectinload(FoodItemUnitConversion.from_unit),
            selectinload(FoodItem.unit_conversions).selectinload(FoodItemUnitConversion.to_unit)
        )
        .where(FoodItem.id == food_item_id)
    )

    if not food_item:
        return []

    available_units = []
    unit_ids_seen = set()

    # Always add base unit
    available_units.append((food_item.base_unit_id, food_item.base_unit.name))
    unit_ids_seen.add(food_item.base_unit_id)

    # Add units from food-specific conversions
    if hasattr(food_item, 'unit_conversions') and food_item.unit_conversions:
        for conversion in food_item.unit_conversions:
            # Add from_unit if not already present
            if conversion.from_unit_id not in unit_ids_seen:
                available_units.append((conversion.from_unit_id, conversion.from_unit.name))
                unit_ids_seen.add(conversion.from_unit_id)

            # Add to_unit if not already present
            if conversion.to_unit_id not in unit_ids_seen:
                available_units.append((conversion.to_unit_id, conversion.to_unit.name))
                unit_ids_seen.add(conversion.to_unit_id)

    return available_units
