"""CRUD operations for core unit system."""

from __future__ import annotations

from sqlalchemy import select, ColumnElement
from sqlalchemy.orm import Session, selectinload

from app.core.enums import UnitType
from app.models.core import Unit, UnitConversion
from app.schemas.core import (
    ConversionResult,
    UnitConversionCreate,
    UnitConversionRead,
    UnitConversionUpdate,
    UnitCreate,
    UnitRead,
    UnitUpdate,
    UnitWithConversions
)


# ================================================================== #
# Schema Conversion Helpers                                          #
# ================================================================== #

def build_unit_read(unit_orm: Unit) -> UnitRead:
    """Convert Unit ORM to Read schema.
    
    Args:
        unit_orm: Unit ORM object
        
    Returns:
        UnitRead schema
    """
    return UnitRead(
        id=unit_orm.id,
        name=unit_orm.name,
        type=unit_orm.type,
        to_base_factor=unit_orm.to_base_factor,
        created_at=unit_orm.created_at
    )


def build_unit_conversion_read(
        conversion_orm: UnitConversion,
        include_unit_names: bool = True
) -> UnitConversionRead:
    """Convert UnitConversion ORM to Read schema.
    
    Args:
        conversion_orm: UnitConversion ORM object with loaded relationships
        include_unit_names: Whether to include unit names (requires loaded relationships)
        
    Returns:
        UnitConversionRead schema
    """
    return UnitConversionRead(
        from_unit_id=conversion_orm.from_unit_id,
        to_unit_id=conversion_orm.to_unit_id,
        factor=conversion_orm.factor,
        from_unit_name=conversion_orm.from_unit.name if include_unit_names and conversion_orm.from_unit else None,
        to_unit_name=conversion_orm.to_unit.name if include_unit_names and conversion_orm.to_unit else None
    )


# ================================================================== #
# Unit CRUD Operations - Schema Returns                             #
# ================================================================== #

def create_unit(db: Session, unit_data: UnitCreate) -> UnitRead:
    """Create a new unit.
    
    Args:
        db: Database session
        unit_data: Unit creation data
        
    Returns:
        Created unit schema
        
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

    return build_unit_read(db_unit)


def get_unit_by_id(db: Session, unit_id: int) -> UnitRead | None:
    """Get unit by ID - returns schema.
    
    Args:
        db: Database session
        unit_id: Unit ID to fetch
        
    Returns:
        Unit schema or None if not found
    """
    unit_orm = db.scalar(
        select(Unit).where(Unit.id == unit_id)
    )

    if not unit_orm:
        return None

    return build_unit_read(unit_orm)


def get_unit_by_name(db: Session, unit_name: str) -> UnitRead | None:
    """Get unit by name - returns schema.
    
    Args:
        db: Database session
        unit_name: Unit name to search for
        
    Returns:
        Unit schema or None if not found
    """
    unit_orm = db.scalar(
        select(Unit).where(Unit.name == unit_name.lower())
    )

    if not unit_orm:
        return None

    return build_unit_read(unit_orm)


def get_all_units(
        db: Session,
        unit_type: UnitType | None = None
) -> list[UnitRead]:
    """Get all units, optionally filtered by type - returns schemas.
    
    Args:
        db: Database session
        unit_type: Optional unit type filter
        
    Returns:
        List of unit schemas
    """
    query = select(Unit).order_by(Unit.name)
    
    if unit_type:
        query = query.where(Unit.type == unit_type)

    units_orm = db.scalars(query).all()

    return [build_unit_read(unit) for unit in units_orm]


def get_units_by_type(db: Session, unit_type: UnitType) -> list[UnitRead]:
    """Get all units of a specific type - returns schemas.
    
    Args:
        db: Database session
        unit_type: Unit type to filter by
        
    Returns:
        List of unit schemas of the specified type
    """
    units_orm = db.scalars(
        select(Unit)
        .where(Unit.type == unit_type)
        .order_by(Unit.name)
    ).all()

    return [build_unit_read(unit) for unit in units_orm]


def update_unit(
        db: Session,
        unit_id: int,
        unit_data: UnitUpdate
) -> UnitRead | None:
    """Update an existing unit.
    
    Args:
        db: Database session
        unit_id: Unit ID to update
        unit_data: Updated unit data
        
    Returns:
        Updated unit schema or None if not found
    """
    db_unit = db.scalar(
        select(Unit).where(Unit.id == unit_id)
    )

    if not db_unit:
        return None

    update_data = unit_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_unit, field, value)
    
    db.commit()
    db.refresh(db_unit)

    return build_unit_read(db_unit)


def delete_unit(db: Session, unit_id: int) -> bool:
    """Delete a unit.
    
    Args:
        db: Database session
        unit_id: Unit ID to delete
        
    Returns:
        True if deleted, False if not found
        
    Note:
        This will fail if the unit has dependent conversions.
        Use has_unit_conversions() to check first.
    """
    db_unit = db.scalar(
        select(Unit).where(Unit.id == unit_id)
    )

    if not db_unit:
        return False

    db.delete(db_unit)
    db.commit()

    return True


def has_unit_conversions(db: Session, unit_id: int) -> bool:
    """Check if a unit has any conversion relationships.
    
    Args:
        db: Database session
        unit_id: Unit ID to check
        
    Returns:
        True if unit has conversions, False otherwise
    """
    conversion_count = db.scalar(
        select(UnitConversion)
        .where(
            (UnitConversion.from_unit_id == unit_id) |
            (UnitConversion.to_unit_id == unit_id)
        )
        .limit(1)
    )

    return conversion_count is not None


# ================================================================== #
# Unit Conversion CRUD Operations - Schema Returns                  #
# ================================================================== #

def create_unit_conversion(
        db: Session,
        conversion_data: UnitConversionCreate
) -> UnitConversionRead:
    """Create a new unit conversion.
    
    Args:
        db: Database session
        conversion_data: Conversion creation data
        
    Returns:
        Created conversion schema with unit names
        
    Raises:
        IntegrityError: If conversion already exists
    """
    db_conversion = UnitConversion(
        from_unit_id=conversion_data.from_unit_id,
        to_unit_id=conversion_data.to_unit_id,
        factor=conversion_data.factor
    )

    db.add(db_conversion)
    db.commit()
    db.refresh(db_conversion)

    # Load relationships for schema conversion
    db_conversion = db.scalar(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .where(
            (UnitConversion.from_unit_id == conversion_data.from_unit_id) &
            (UnitConversion.to_unit_id == conversion_data.to_unit_id)
        )
    )

    return build_unit_conversion_read(db_conversion)


def get_unit_conversion(
        db: Session,
        from_unit_id: int,
        to_unit_id: int
) -> UnitConversionRead | None:
    """Get a specific unit conversion - returns schema.
    
    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID
        
    Returns:
        Conversion schema with unit names or None if not found
    """
    conversion_orm = db.scalar(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .where(
            (UnitConversion.from_unit_id == from_unit_id) &
            (UnitConversion.to_unit_id == to_unit_id)
        )
    )

    if not conversion_orm:
        return None

    return build_unit_conversion_read(conversion_orm)



def get_conversion_factor(
    db: Session,
    from_unit_id: int,
    to_unit_id: int
) -> float | None | ColumnElement[float]:
    """
    Determine the conversion factor between two units.

    Args:
        db: SQLAlchemy session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Conversion factor as float or None if conversion is not possible
    """

    if from_unit_id == to_unit_id:
        return 1.0

    # Try direct conversion
    direct = db.scalar(
        select(UnitConversion).where(
            (UnitConversion.from_unit_id == from_unit_id) &
            (UnitConversion.to_unit_id == to_unit_id)
        )
    )
    if direct:
        return direct.factor

    # Try reverse conversion
    reverse = db.scalar(
        select(UnitConversion).where(
            (UnitConversion.from_unit_id == to_unit_id) &
            (UnitConversion.to_unit_id == from_unit_id)
        )
    )
    if reverse:
        return 1.0 / reverse.factor

    # Try base unit conversion
    from_unit: Unit | None = db.scalar(select(Unit).where(Unit.id == from_unit_id))
    to_unit: Unit | None = db.scalar(select(Unit).where(Unit.id == to_unit_id))

    if not from_unit or not to_unit:
        return None

    if from_unit.type != to_unit.type:
        return None

    # Final fallback: convert through base unit
    try:
        return from_unit.to_base_factor / to_unit.to_base_factor
    except ZeroDivisionError:
        return None


def get_conversions_from_unit(db: Session, unit_id: int) -> list[UnitConversionRead]:
    """Get all conversions from a specific unit - returns schemas.
    
    Args:
        db: Database session
        unit_id: Source unit ID
        
    Returns:
        List of conversion schemas with unit names
    """
    conversions_orm = db.scalars(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .where(UnitConversion.from_unit_id == unit_id)
        .order_by(UnitConversion.to_unit_id)
    ).all()

    return [build_unit_conversion_read(conv) for conv in conversions_orm]


def get_conversions_to_unit(db: Session, unit_id: int) -> list[UnitConversionRead]:
    """Get all conversions to a specific unit - returns schemas.
    
    Args:
        db: Database session
        unit_id: Target unit ID
        
    Returns:
        List of conversion schemas with unit names
    """
    conversions_orm = db.scalars(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .where(UnitConversion.to_unit_id == unit_id)
        .order_by(UnitConversion.from_unit_id)
    ).all()

    return [build_unit_conversion_read(conv) for conv in conversions_orm]


def get_all_unit_conversions(db: Session) -> list[UnitConversionRead]:
    """Get all unit conversions - returns schemas.
    
    Args:
        db: Database session
        
    Returns:
        List of all conversion schemas with unit names
    """
    conversions_orm = db.scalars(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .order_by(UnitConversion.from_unit_id, UnitConversion.to_unit_id)
    ).all()

    return [build_unit_conversion_read(conv) for conv in conversions_orm]


def update_unit_conversion(
        db: Session,
        from_unit_id: int,
        to_unit_id: int,
        conversion_data: UnitConversionUpdate
) -> UnitConversionRead | None:
    """Update an existing unit conversion.
    
    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID
        conversion_data: Updated conversion data
        
    Returns:
        Updated conversion schema with unit names or None if not found
    """
    db_conversion = db.scalar(
        select(UnitConversion)
        .options(
            selectinload(UnitConversion.from_unit),
            selectinload(UnitConversion.to_unit)
        )
        .where(
            (UnitConversion.from_unit_id == from_unit_id) &
            (UnitConversion.to_unit_id == to_unit_id)
        )
    )

    if not db_conversion:
        return None

    # Only factor can be updated
    db_conversion.factor = conversion_data.factor
    
    db.commit()
    db.refresh(db_conversion)

    return build_unit_conversion_read(db_conversion)


def delete_unit_conversion(
        db: Session,
        from_unit_id: int,
        to_unit_id: int
) -> bool:
    """Delete a unit conversion.
    
    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID
        
    Returns:
        True if deleted, False if not found
    """
    db_conversion = db.scalar(
        select(UnitConversion)
        .where(
            (UnitConversion.from_unit_id == from_unit_id) &
            (UnitConversion.to_unit_id == to_unit_id)
        )
    )

    if not db_conversion:
        return False

    db.delete(db_conversion)
    db.commit()

    return True


# ================================================================== #
# Conversion Calculation Operations - Schema Returns                #
# ================================================================== #

def convert_value(
        db: Session,
        value: float,
        from_unit_id: int,
        to_unit_id: int
) -> float | None:
    """Convert a value between units.
    
    Args:
        db: Database session
        value: Value to convert
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID
        
    Returns:
        Converted value or None if conversion not possible
    """
    factor = get_conversion_factor(db, from_unit_id, to_unit_id)

    if factor is None:
        return None

    return value * factor


def can_convert_units(
        db: Session,
        from_unit_id: int,
        to_unit_id: int
) -> bool:
    """Check if conversion between two units is possible.
    
    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID
        
    Returns:
        True if conversion is possible, False otherwise
    """
    return get_conversion_factor(db, from_unit_id, to_unit_id) is not None


def get_unit_with_conversions(db: Session, unit_id: int) -> UnitWithConversions | None:
    """Get unit with all its available conversions - returns schema.
    
    Args:
        db: Database session
        unit_id: Unit ID
        
    Returns:
        UnitWithConversions schema or None if unit not found
    """
    unit_schema = get_unit_by_id(db, unit_id)
    if not unit_schema:
        return None

    conversions = get_conversions_from_unit(db, unit_id)

    return UnitWithConversions(
        **unit_schema.model_dump(),
        available_conversions=conversions
    )


def create_conversion_result(
        db: Session,
        original_value: float,
        converted_value: float,
        from_unit_id: int,
        to_unit_id: int,
        conversion_factor: float
) -> ConversionResult:
    """Create a conversion result schema.
    
    Args:
        db: Database session
        original_value: Original value
        converted_value: Converted value
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID
        conversion_factor: Factor used in conversion
        
    Returns:
        ConversionResult schema with unit names
    """
    from_unit = get_unit_by_id(db, from_unit_id)
    to_unit = get_unit_by_id(db, to_unit_id)

    return ConversionResult(
        original_value=original_value,
        original_unit_id=from_unit_id,
        original_unit_name=from_unit.name if from_unit else f"Unit {from_unit_id}",
        converted_value=converted_value,
        target_unit_id=to_unit_id,
        target_unit_name=to_unit.name if to_unit else f"Unit {to_unit_id}",
        conversion_factor=conversion_factor
    )
