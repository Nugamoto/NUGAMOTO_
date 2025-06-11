"""CRUD operations for food system."""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.models.food import FoodItem, FoodItemUnitConversion, FoodItemAlias
from app.schemas.food import (
    FoodItemCreate, FoodItemUpdate, FoodItemUnitConversionCreate, FoodItemAliasCreate
)


# ================================================================== #
# FoodItem CRUD Operations                                           #
# ================================================================== #

def create_food_item(db: Session, food_item_data: FoodItemCreate) -> FoodItem:
    """Create a new food item.

    Args:
        db: Database session
        food_item_data: Food item creation data

    Returns:
        Created food item instance

    Raises:
        IntegrityError: If food item name already exists or base_unit_id doesn't exist
    """
    # TODO: Add validation that base_unit_id exists in units table

    db_food_item = FoodItem(
        name=food_item_data.name,
        category=food_item_data.category,
        base_unit_id=food_item_data.base_unit_id
    )

    db.add(db_food_item)
    db.commit()
    db.refresh(db_food_item)

    return db_food_item


def get_food_item_by_id(db: Session, food_item_id: int) -> FoodItem | None:
    """Get food item by ID.

    Args:
        db: Database session
        food_item_id: Food item ID to fetch

    Returns:
        Food item instance or None if not found
    """
    return db.scalar(
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItem.id == food_item_id)
    )


def get_food_item_by_name(db: Session, food_item_name: str) -> FoodItem | None:
    """Get food item by name.

    Args:
        db: Database session
        food_item_name: Food item name to search for

    Returns:
        Food item instance or None if not found
    """
    return db.scalar(
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItem.name == food_item_name.strip().title())
    )


def get_all_food_items(
        db: Session,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[FoodItem]:
    """Get all food items with optional filtering.

    Args:
        db: Database session
        category: Optional category filter
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of food item instances
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

    return list(db.scalars(query).all())


def get_food_items_by_category(db: Session, category: str) -> list[FoodItem]:
    """Get all food items in a specific category.

    Args:
        db: Database session
        category: Category to filter by

    Returns:
        List of food item instances in the specified category
    """
    return list(db.scalars(
        select(FoodItem)
        .options(selectinload(FoodItem.base_unit))
        .where(FoodItem.category == category.strip().title())
        .order_by(FoodItem.name)
    ).all())


def update_food_item(
        db: Session,
        food_item_id: int,
        food_item_data: FoodItemUpdate
) -> FoodItem | None:
    """Update an existing food item.

    Args:
        db: Database session
        food_item_id: Food item ID to update
        food_item_data: Updated food item data

    Returns:
        Updated food item instance or None if not found
    """
    db_food_item = get_food_item_by_id(db, food_item_id)
    if not db_food_item:
        return None

    update_data = food_item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_food_item, field, value)

    db.commit()
    db.refresh(db_food_item)

    return db_food_item


def delete_food_item(db: Session, food_item_id: int) -> bool:
    """Delete a food item.

    Args:
        db: Database session
        food_item_id: Food item ID to delete

    Returns:
        True if deleted, False if not found
    """
    db_food_item = get_food_item_by_id(db, food_item_id)
    if not db_food_item:
        return False

    db.delete(db_food_item)
    db.commit()

    return True


# ================================================================== #
# FoodItemAlias CRUD Operations                                      #
# ================================================================== #

def create_food_item_alias(
        db: Session,
        alias_data: FoodItemAliasCreate
) -> FoodItemAlias:
    """Create a new food item alias.

    Args:
        db: Database session
        alias_data: Alias creation data

    Returns:
        Created alias instance

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

    return db_alias


def get_aliases_for_food_item(
        db: Session,
        food_item_id: int,
        user_id: int | None = None
) -> list[FoodItemAlias]:
    """Get all aliases for a specific food item.

    Args:
        db: Database session
        food_item_id: Food item ID
        user_id: Optional user ID to filter user-specific aliases

    Returns:
        List of alias instances for the food item
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

    return list(db.scalars(query).all())


def get_all_aliases_for_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[FoodItemAlias]:
    """Get all aliases created by a specific user.

    Args:
        db: Database session
        user_id: User ID
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of alias instances created by the user
    """
    return list(db.scalars(
        select(FoodItemAlias)
        .options(
            selectinload(FoodItemAlias.food_item),
            selectinload(FoodItemAlias.user)
        )
        .where(FoodItemAlias.user_id == user_id)
        .order_by(FoodItemAlias.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all())


def get_alias_by_id(db: Session, alias_id: int) -> FoodItemAlias | None:
    """Get alias by ID.

    Args:
        db: Database session
        alias_id: Alias ID to fetch

    Returns:
        Alias instance or None if not found
    """
    return db.scalar(
        select(FoodItemAlias)
        .options(
            selectinload(FoodItemAlias.food_item),
            selectinload(FoodItemAlias.user)
        )
        .where(FoodItemAlias.id == alias_id)
    )


def delete_alias_by_id(db: Session, alias_id: int) -> bool:
    """Delete an alias by ID.

    Args:
        db: Database session
        alias_id: Alias ID to delete

    Returns:
        True if deleted, False if not found
    """
    db_alias = get_alias_by_id(db, alias_id)
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
) -> list[FoodItem]:
    """Search food items by alias term.

    Args:
        db: Database session
        alias_term: Term to search for in aliases
        user_id: Optional user ID to include user-specific aliases
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of food items that have matching aliases
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

    return list(db.scalars(query).all())


# ================================================================== #
# FoodItemUnitConversion CRUD Operations                             #
# ================================================================== #

def create_food_unit_conversion(
        db: Session,
        conversion_data: FoodItemUnitConversionCreate
) -> FoodItemUnitConversion:
    """Create a new food item unit conversion.

    Args:
        db: Database session
        conversion_data: Unit conversion creation data

    Returns:
        Created unit conversion instance

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

    return db_conversion


def get_food_unit_conversion(
        db: Session,
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> FoodItemUnitConversion | None:
    """Get specific food item unit conversion.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Unit conversion instance or None if not found
    """
    return db.scalar(
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


def get_conversion_for_food_item(
        db: Session,
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> float | None:
    """Get conversion factor for a specific food item between units.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Conversion factor or None if conversion doesn't exist
    """
    conversion = get_food_unit_conversion(db, food_item_id, from_unit_id, to_unit_id)
    return conversion.factor if conversion else None


def get_conversions_for_food_item(
        db: Session,
        food_item_id: int
) -> list[FoodItemUnitConversion]:
    """Get all unit conversions for a specific food item.

    Args:
        db: Database session
        food_item_id: Food item ID

    Returns:
        List of unit conversion instances
    """
    return list(db.scalars(
        select(FoodItemUnitConversion)
        .options(
            selectinload(FoodItemUnitConversion.from_unit),
            selectinload(FoodItemUnitConversion.to_unit)
        )
        .where(FoodItemUnitConversion.food_item_id == food_item_id)
        .order_by(FoodItemUnitConversion.from_unit_id, FoodItemUnitConversion.to_unit_id)
    ).all())


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
    conversion = get_food_unit_conversion(db, food_item_id, from_unit_id, to_unit_id)
    if not conversion:
        return False

    db.delete(conversion)
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
    """Convert a value for a specific food item between units.

    Args:
        db: Database session
        food_item_id: Food item ID
        value: Value to convert
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Tuple of (converted_value, is_food_specific) or None if conversion is not possible
        is_food_specific indicates whether a food-specific conversion was used
    """
    if from_unit_id == to_unit_id:
        return value, False

    # Try food-specific conversion first
    factor = get_conversion_for_food_item(db, food_item_id, from_unit_id, to_unit_id)
    if factor is not None:
        return value * factor, True

    # Fall back to generic unit conversion if available
    from app.crud import core as crud_core
    factor = crud_core.get_conversion_factor(db, from_unit_id, to_unit_id)
    if factor is not None:
        return value * factor, False

    return None


def can_convert_food_units(
        db: Session,
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> bool:
    """Check if conversion between two units is possible for a specific food item.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        True if conversion is possible, False otherwise
    """
    if from_unit_id == to_unit_id:
        return True

    # Check food-specific conversion
    if get_conversion_for_food_item(db, food_item_id, from_unit_id, to_unit_id) is not None:
        return True

    # Check generic unit conversion
    from app.crud import core as crud_core
    return crud_core.can_convert_units(db, from_unit_id, to_unit_id)