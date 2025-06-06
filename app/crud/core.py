"""CRUD operations for core unit system."""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.models.core import Unit, UnitConversion, UnitType
from app.schemas.core import UnitCreate, UnitConversionCreate


# ================================================================== #
# Unit CRUD Operations                                               #
# ================================================================== #

def create_unit(db: Session, unit_data: UnitCreate) -> Unit:
    """Create a new unit.

    Args:
        db: Database session
        unit_data: Unit creation data

    Returns:
        Created unit instance

    Raises:
        IntegrityError: If unit name already exists
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
    """Get unit by ID.

    Args:
        db: Database session
        unit_id: Unit ID to fetch

    Returns:
        Unit instance or None if not found
    """
    return db.scalar(
        select(Unit).where(Unit.id == unit_id)
    )


def get_unit_by_name(db: Session, unit_name: str) -> Unit | None:
    """Get unit by name.

    Args:
        db: Database session
        unit_name: Unit name to search for

    Returns:
        Unit instance or None if not found
    """
    return db.scalar(
        select(Unit).where(Unit.name == unit_name.lower().strip())
    )


def get_all_units(db: Session, unit_type: UnitType | None = None) -> list[Unit]:
    """Get all units, optionally filtered by type.

    Args:
        db: Database session
        unit_type: Optional unit type filter

    Returns:
        List of unit instances
    """
    query = select(Unit).order_by(Unit.type, Unit.name)

    if unit_type:
        query = query.where(Unit.type == unit_type)

    return list(db.scalars(query).all())


def get_units_by_type(db: Session, unit_type: UnitType) -> list[Unit]:
    """Get all units of a specific type.

    Args:
        db: Database session
        unit_type: Unit type to filter by

    Returns:
        List of unit instances of the specified type
    """
    return list(db.scalars(
        select(Unit)
        .where(Unit.type == unit_type)
        .order_by(Unit.name)
    ).all())


# ================================================================== #
# Unit Conversion CRUD Operations                                    #
# ================================================================== #

def create_unit_conversion(
        db: Session,
        conversion_data: UnitConversionCreate
) -> UnitConversion:
    """Create a new unit conversion.

    Args:
        db: Database session
        conversion_data: Unit conversion creation data

    Returns:
        Created unit conversion instance

    Raises:
        IntegrityError: If conversion already exists or units don't exist
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
    """Get specific unit conversion.

    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Unit conversion instance or None if not found
    """
    return db.scalar(
        select(UnitConversion).where(
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
) -> float | None:
    """Get conversion factor between two units.

    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Conversion factor or None if conversion doesn't exist
    """
    conversion = get_unit_conversion(db, from_unit_id, to_unit_id)
    return conversion.factor if conversion else None


def get_conversions_from_unit(db: Session, unit_id: int) -> list[UnitConversion]:
    """Get all conversions from a specific unit.

    Args:
        db: Database session
        unit_id: Source unit ID

    Returns:
        List of unit conversion instances
    """
    return list(db.scalars(
        select(UnitConversion)
        .options(selectinload(UnitConversion.to_unit))
        .where(UnitConversion.from_unit_id == unit_id)
        .order_by(UnitConversion.to_unit_id)
    ).all())


def get_conversions_to_unit(db: Session, unit_id: int) -> list[UnitConversion]:
    """Get all conversions to a specific unit.

    Args:
        db: Database session
        unit_id: Target unit ID

    Returns:
        List of unit conversion instances
    """
    return list(db.scalars(
        select(UnitConversion)
        .options(selectinload(UnitConversion.from_unit))
        .where(UnitConversion.to_unit_id == unit_id)
        .order_by(UnitConversion.from_unit_id)
    ).all())


def get_all_unit_conversions(db: Session) -> list[UnitConversion]:
    """Get all unit conversions.

    Args:
        db: Database session

    Returns:
        List of all unit conversion instances
    """
    return list(db.scalars(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .order_by(UnitConversion.from_unit_id, UnitConversion.to_unit_id)
    ).all())


# ================================================================== #
# Conversion Calculation Helper                                      #
# ================================================================== #

def convert_value(
        db: Session,
        value: float,
        from_unit_id: int,
        to_unit_id: int
) -> float | None:
    """Convert a value from one unit to another.

    Args:
        db: Database session
        value: Value to convert
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Converted value or None if conversion is not possible
    """
    if from_unit_id == to_unit_id:
        return value

    factor = get_conversion_factor(db, from_unit_id, to_unit_id)
    if factor is None:
        return None

    return value * factor


def can_convert_units(db: Session, from_unit_id: int, to_unit_id: int) -> bool:
    """Check if conversion between two units is possible.

    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        True if conversion is possible, False otherwise
    """
    if from_unit_id == to_unit_id:
        return True

    return get_conversion_factor(db, from_unit_id, to_unit_id) is not None