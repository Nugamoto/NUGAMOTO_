"""API endpoints for core unit system."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud
from app.core.dependencies import get_db
from app.models.core import UnitType
from app.schemas.core import (
    ConversionResult,
    UnitConversionCreate,
    UnitConversionRead,
    UnitCreate,
    UnitRead,
    UnitWithConversions
)

router = APIRouter()


# ================================================================== #
# Unit Endpoints                                                     #
# ================================================================== #

@router.post("/units/", response_model=UnitRead, status_code=status.HTTP_201_CREATED)
def create_unit(
        *,
        db: Annotated[Session, Depends(get_db)],
        unit_data: UnitCreate
) -> UnitRead:
    """Create a new unit.

    Args:
        db: Database session
        unit_data: Unit creation data

    Returns:
        Created unit data

    Raises:
        HTTPException: 400 if unit name already exists
    """
    try:
        unit = crud.core.create_unit(db=db, unit_data=unit_data)
        return UnitRead.model_validate(unit)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit with name '{unit_data.name}' already exists"
        )


@router.get("/units/", response_model=list[UnitRead])
def get_units(
        *,
        db: Annotated[Session, Depends(get_db)],
        unit_type: Annotated[UnitType | None, Query(description="Filter by unit type")] = None
) -> list[UnitRead]:
    """Get all units, optionally filtered by type.

    Args:
        db: Database session
        unit_type: Optional unit type filter

    Returns:
        List of units
    """
    units = crud.core.get_all_units(db=db, unit_type=unit_type)
    return [UnitRead.model_validate(unit) for unit in units]


@router.get("/units/{unit_id}", response_model=UnitRead)
def get_unit_by_id(
        *,
        db: Annotated[Session, Depends(get_db)],
        unit_id: int
) -> UnitRead:
    """Get unit by ID.

    Args:
        db: Database session
        unit_id: Unit ID to fetch

    Returns:
        Unit data

    Raises:
        HTTPException: 404 if unit not found
    """
    unit = crud.core.get_unit_by_id(db=db, unit_id=unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found"
        )
    return UnitRead.model_validate(unit)


@router.get("/units/{unit_id}/conversions", response_model=UnitWithConversions)
def get_unit_with_conversions(
        *,
        db: Annotated[Session, Depends(get_db)],
        unit_id: int
) -> UnitWithConversions:
    """Get unit with available conversions.

    Args:
        db: Database session
        unit_id: Unit ID to fetch

    Returns:
        Unit data with available conversions

    Raises:
        HTTPException: 404 if unit not found
    """
    unit = crud.core.get_unit_by_id(db=db, unit_id=unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found"
        )

    conversions = crud.core.get_conversions_from_unit(db=db, unit_id=unit_id)
    conversion_reads = []

    for conversion in conversions:
        conversion_reads.append(UnitConversionRead(
            from_unit_id=conversion.from_unit_id,
            to_unit_id=conversion.to_unit_id,
            factor=conversion.factor,
            from_unit_name=conversion.from_unit.name,
            to_unit_name=conversion.to_unit.name
        ))

    return UnitWithConversions(
        **UnitRead.model_validate(unit).model_dump(),
        available_conversions=conversion_reads
    )


# ================================================================== #
# Unit Conversion Endpoints                                          #
# ================================================================== #

@router.post(
    "/unit-conversions/",
    response_model=UnitConversionRead,
    status_code=status.HTTP_201_CREATED
)
def create_unit_conversion(
        *,
        db: Annotated[Session, Depends(get_db)],
        conversion_data: UnitConversionCreate
) -> UnitConversionRead:
    """Create a new unit conversion.

    Args:
        db: Database session
        conversion_data: Unit conversion creation data

    Returns:
        Created unit conversion data

    Raises:
        HTTPException: 400 if conversion already exists or units don't exist
    """
    # Validate that both units exist
    from_unit = crud.core.get_unit_by_id(db=db, unit_id=conversion_data.from_unit_id)
    to_unit = crud.core.get_unit_by_id(db=db, unit_id=conversion_data.to_unit_id)

    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source unit with ID {conversion_data.from_unit_id} not found"
        )

    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target unit with ID {conversion_data.to_unit_id} not found"
        )

    try:
        conversion = crud.core.create_unit_conversion(db=db, conversion_data=conversion_data)
        return UnitConversionRead(
            from_unit_id=conversion.from_unit_id,
            to_unit_id=conversion.to_unit_id,
            factor=conversion.factor,
            from_unit_name=from_unit.name,
            to_unit_name=to_unit.name
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversion from unit {conversion_data.from_unit_id} to unit {conversion_data.to_unit_id} already exists"
        )


@router.get("/unit-conversions/", response_model=list[UnitConversionRead])
def get_unit_conversions(
        *,
        db: Annotated[Session, Depends(get_db)],
        from_unit_id: Annotated[int | None, Query(description="Filter by source unit ID")] = None,
        to_unit_id: Annotated[int | None, Query(description="Filter by target unit ID")] = None
) -> list[UnitConversionRead]:
    """Get unit conversions with optional filtering.

    Args:
        db: Database session
        from_unit_id: Optional source unit ID filter
        to_unit_id: Optional target unit ID filter

    Returns:
        List of unit conversions
    """
    if from_unit_id and to_unit_id:
        # Get specific conversion
        conversion = crud.core.get_unit_conversion(
            db=db,
            from_unit_id=from_unit_id,
            to_unit_id=to_unit_id
        )
        if not conversion:
            return []
        conversions = [conversion]
    elif from_unit_id:
        # Get all conversions from a unit
        conversions = crud.core.get_conversions_from_unit(db=db, unit_id=from_unit_id)
    elif to_unit_id:
        # Get all conversions to a unit
        conversions = crud.core.get_conversions_to_unit(db=db, unit_id=to_unit_id)
    else:
        # Get all conversions
        conversions = crud.core.get_all_unit_conversions(db=db)

    result = []
    for conversion in conversions:
        result.append(UnitConversionRead(
            from_unit_id=conversion.from_unit_id,
            to_unit_id=conversion.to_unit_id,
            factor=conversion.factor,
            from_unit_name=conversion.from_unit.name,
            to_unit_name=conversion.to_unit.name
        ))

    return result


# ================================================================== #
# Conversion Calculation Endpoints                                   #
# ================================================================== #

@router.post("/convert/", response_model=ConversionResult)
def convert_units(
        *,
        db: Annotated[Session, Depends(get_db)],
        value: Annotated[float, Query(description="Value to convert", gt=0)],
        from_unit_id: Annotated[int, Query(description="Source unit ID")],
        to_unit_id: Annotated[int, Query(description="Target unit ID")]
) -> ConversionResult:
    """Convert a value from one unit to another.

    Args:
        db: Database session
        value: Value to convert
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Conversion result with original and converted values

    Raises:
        HTTPException: 400 if units don't exist or conversion is not possible
    """
    # Validate that both units exist
    from_unit = crud.core.get_unit_by_id(db=db, unit_id=from_unit_id)
    to_unit = crud.core.get_unit_by_id(db=db, unit_id=to_unit_id)

    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source unit with ID {from_unit_id} not found"
        )

    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target unit with ID {to_unit_id} not found"
        )

    # Perform conversion
    converted_value = crud.core.convert_value(
        db=db,
        value=value,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )

    if converted_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No conversion available from '{from_unit.name}' to '{to_unit.name}'"
        )

    # Calculate the conversion factor used
    if from_unit_id == to_unit_id:
        factor = 1.0
    else:
        factor = crud.core.get_conversion_factor(db=db, from_unit_id=from_unit_id, to_unit_id=to_unit_id)

    return ConversionResult(
        original_value=value,
        original_unit_id=from_unit_id,
        original_unit_name=from_unit.name,
        converted_value=converted_value,
        target_unit_id=to_unit_id,
        target_unit_name=to_unit.name,
        conversion_factor=factor
    )


@router.get("/can-convert/")
def can_convert_units(
        *,
        db: Annotated[Session, Depends(get_db)],
        from_unit_id: Annotated[int, Query(description="Source unit ID")],
        to_unit_id: Annotated[int, Query(description="Target unit ID")]
) -> dict[str, bool]:
    """Check if conversion between two units is possible.

    Args:
        db: Database session
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Dictionary with conversion possibility status
    """
    can_convert = crud.core.can_convert_units(
        db=db,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )

    return {"can_convert": can_convert}
