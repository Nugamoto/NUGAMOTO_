"""CRUD operations for core unit system."""

from __future__ import annotations

from sqlalchemy import and_, select, func, ColumnElement
from sqlalchemy.orm import Session, selectinload

from app.core.enums import UnitType
from app.models.core import Unit, UnitConversion
from app.schemas.core import UnitCreate, UnitConversionCreate, UnitUpdate, UnitConversionUpdate


# ================================================================== #
# Unit CRUD Operations                                               #
# ================================================================== #

def create_unit(db: Session, unit_data: UnitCreate) -> Unit:
    """Create a new unit in the system.

    Args:
        db: Database session.
        unit_data: Validated unit creation data.

    Returns:
        The newly created and persisted unit instance.

    Raises:
        IntegrityError: If unit name already exists (handled by caller).
    """
    db_unit = Unit(
        name=unit_data.name,
        type=unit_data.type,
        to_base_factor=unit_data.to_base_factor
    )

    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)

    return db_unit


def get_unit_by_id(db: Session, unit_id: int) -> Unit | None:
    """Retrieve a unit by its unique identifier.

    Args:
        db: Database session.
        unit_id: The unique identifier of the unit.

    Returns:
        Unit instance if found, None otherwise.
    """
    return db.scalar(
        select(Unit).where(Unit.id == unit_id)
    )


def get_unit_by_name(db: Session, unit_name: str) -> Unit | None:
    """Retrieve a unit by its name (case-insensitive).

    Args:
        db: Database session.
        unit_name: The name of the unit to search for.

    Returns:
        Unit instance if found, None otherwise.
    """
    return db.scalar(
        select(Unit).where(Unit.name == unit_name.lower().strip())
    )


def get_all_units(db: Session, unit_type: UnitType | None = None) -> list[Unit]:
    """Retrieve all units, optionally filtered by type.

    Args:
        db: Database session.
        unit_type: Optional filter to get units of a specific type only.

    Returns:
        List of unit instances, ordered by type and name.
    """
    query = select(Unit).order_by(Unit.type, Unit.name)

    if unit_type:
        query = query.where(Unit.type == unit_type)

    return list(db.scalars(query).all())


def get_units_by_type(db: Session, unit_type: UnitType) -> list[Unit]:
    """Retrieve all units of a specific type.

    Args:
        db: Database session.
        unit_type: The unit type to filter by.

    Returns:
        List of unit instances of the specified type, ordered by name.
    """
    return list(db.scalars(
        select(Unit)
        .where(Unit.type == unit_type)
        .order_by(Unit.name)
    ).all())


def update_unit(db: Session, unit_id: int, unit_data: UnitUpdate) -> Unit | None:
    """Update an existing unit with partial data.

    Args:
        db: Database session.
        unit_id: The unique identifier of the unit to update.
        unit_data: Partial unit data to update (only non-None fields are updated).

    Returns:
        Updated unit instance if found, None otherwise.

    Raises:
        IntegrityError: If updated name conflicts with existing unit (handled by caller).
    """
    unit = get_unit_by_id(db, unit_id)
    if not unit:
        return None

    # Update only the fields that are not None
    update_data = unit_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(unit, field, value)

    db.commit()
    db.refresh(unit)

    return unit


def delete_unit(db: Session, unit_id: int) -> bool:
    """Delete a unit from the system.

    Args:
        db: Database session.
        unit_id: The unique identifier of the unit to delete.

    Returns:
        True if unit was found and deleted, False if unit was not found.

    Note:
        This function checks for existing conversions and prevents deletion
        if any conversions reference this unit.
    """
    unit = get_unit_by_id(db, unit_id)
    if not unit:
        return False

    # Check if there are any conversions using this unit
    conversions_from = get_conversions_from_unit(db, unit_id)
    conversions_to = get_conversions_to_unit(db, unit_id)
    
    if conversions_from or conversions_to:
        # Unit has dependent conversions, cannot delete
        return False

    db.delete(unit)
    db.commit()

    return True


def has_unit_conversions(db: Session, unit_id: int) -> bool:
    """Check if a unit has any associated conversions.

    Args:
        db: Database session.
        unit_id: The unique identifier of the unit to check.

    Returns:
        True if unit has conversions (as source or target), False otherwise.
    """
    stmt = (
        select(func.count())
        .select_from(UnitConversion)
        .where(UnitConversion.from_unit_id == unit_id)
    )

    return db.execute(stmt).scalar_one() > 0

# ================================================================== #
# Unit Conversion CRUD Operations                                    #
# ================================================================== #

def create_unit_conversion(
    db: Session,
    conversion_data: UnitConversionCreate
) -> UnitConversion:
    """Create a new unit conversion relationship.

    Args:
        db: Database session.
        conversion_data: Validated unit conversion creation data.

    Returns:
        The newly created and persisted unit conversion instance.

    Raises:
        IntegrityError: If conversion already exists or units don't exist.
    """
    db_conversion = UnitConversion(
        from_unit_id=conversion_data.from_unit_id,
        to_unit_id=conversion_data.to_unit_id,
        factor=conversion_data.factor
    )

    db.add(db_conversion)
    db.commit()
    db.refresh(db_conversion)

    return db_conversion


def get_unit_conversion(
    db: Session,
    from_unit_id: int,
    to_unit_id: int
) -> UnitConversion | None:
    """Retrieve a specific unit conversion relationship.

    Args:
        db: Database session.
        from_unit_id: Source unit identifier.
        to_unit_id: Target unit identifier.

    Returns:
        Unit conversion instance if found, None otherwise.
    """
    return db.scalar(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .where(
            and_(
                UnitConversion.from_unit_id == from_unit_id,
                UnitConversion.to_unit_id == to_unit_id
            )
        )
    )


def get_conversion_factor(
    db: Session,
    from_unit_id: int,
    to_unit_id: int
) -> float | ColumnElement[float] | None:
    """Get the conversion factor between two units.

    Args:
        db: Database session.
        from_unit_id: Source unit identifier.
        to_unit_id: Target unit identifier.

    Returns:
        Conversion factor if conversion exists, None otherwise.
    """
    if from_unit_id == to_unit_id:
        return 1.0

    conv = get_unit_conversion(db, from_unit_id, to_unit_id)
    if conv:
        return conv.factor

    from_unit = get_unit_by_id(db, from_unit_id)
    to_unit = get_unit_by_id(db, to_unit_id)
    if from_unit and to_unit:
        return from_unit.to_base_factor / to_unit.to_base_factor

    return None

def get_conversions_from_unit(db: Session, unit_id: int) -> list[UnitConversion]:
    """Retrieve all conversions originating from a specific unit.

    Args:
        db: Database session.
        unit_id: Source unit identifier.

    Returns:
        List of unit conversion instances with target units loaded.
    """
    return list(db.scalars(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .where(UnitConversion.from_unit_id == unit_id)
        .order_by(UnitConversion.to_unit_id)
    ).all())


def get_conversions_to_unit(db: Session, unit_id: int) -> list[UnitConversion]:
    """Retrieve all conversions targeting a specific unit.

    Args:
        db: Database session.
        unit_id: Target unit identifier.

    Returns:
        List of unit conversion instances with source units loaded.
    """
    return list(db.scalars(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .where(UnitConversion.to_unit_id == unit_id)
        .order_by(UnitConversion.from_unit_id)
    ).all())


def get_all_unit_conversions(db: Session) -> list[UnitConversion]:
    """Retrieve all unit conversions in the system.

    Args:
        db: Database session.

    Returns:
        List of all unit conversion instances with related units loaded.
    """
    return list(db.scalars(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .order_by(UnitConversion.from_unit_id, UnitConversion.to_unit_id)
    ).all())


def update_unit_conversion(
    db: Session,
    from_unit_id: int,
    to_unit_id: int,
    conversion_data: UnitConversionUpdate
) -> UnitConversion | None:
    """Update an existing unit conversion relationship.

    Args:
        db: Database session.
        from_unit_id: Source unit identifier.
        to_unit_id: Target unit identifier.
        conversion_data: Updated conversion data (factor).

    Returns:
        Updated unit conversion instance if found, None otherwise.
    """
    conversion = get_unit_conversion(db, from_unit_id, to_unit_id)
    if not conversion:
        return None

    # Update the factor
    conversion.factor = conversion_data.factor

    db.commit()
    db.refresh(conversion)

    return conversion


def delete_unit_conversion(
    db: Session,
    from_unit_id: int,
    to_unit_id: int
) -> bool:
    """Delete a unit conversion relationship.

    Args:
        db: Database session.
        from_unit_id: Source unit identifier.
        to_unit_id: Target unit identifier.

    Returns:
        True if conversion was found and deleted, False if conversion was not found.
    """
    conversion = db.scalar(
        select(UnitConversion).where(
            and_(
                UnitConversion.from_unit_id == from_unit_id,
                UnitConversion.to_unit_id == to_unit_id
            )
        )
    )
    
    if not conversion:
        return False

    db.delete(conversion)
    db.commit()

    return True


# ================================================================== #
# Conversion Calculation Helpers                                     #
# ================================================================== #

def convert_value(
    db: Session,
    value: float,
    from_unit_id: int,
    to_unit_id: int
) -> float | None:
    """Convert a numeric value from one unit to another.

    Args:
        db: Database session.
        value: The numeric value to convert.
        from_unit_id: Source unit identifier.
        to_unit_id: Target unit identifier.

    Returns:
        Converted value if conversion is possible, None otherwise.
    """
    if from_unit_id == to_unit_id:
        return value

    factor = get_conversion_factor(db, from_unit_id, to_unit_id)
    if factor is None:
        return None

    return value * factor


def can_convert_units(db: Session, from_unit_id: int, to_unit_id: int) -> bool:
    """Check whether conversion between two units is possible.

    Args:
        db: Database session.
        from_unit_id: Source unit identifier.
        to_unit_id: Target unit identifier.

    Returns:
        True if conversion is possible, False otherwise.
    """
    if from_unit_id == to_unit_id:
        return True

    return get_conversion_factor(db, from_unit_id, to_unit_id) is not None