"""API endpoints for core unit system."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.enums import UnitType
from app.crud import core as crud_core
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

# Create routers with appropriate tags
units_router = APIRouter(prefix="/units", tags=["Unit Management"])
conversions_router = APIRouter(prefix="/units", tags=["Unit Conversion"])


# ================================================================== #
# Unit Management Endpoints                                          #
# ================================================================== #

@units_router.post(
    "/",
    response_model=UnitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new unit"
)
def create_unit(
    unit_data: UnitCreate,
    db: Annotated[Session, Depends(get_db)]
) -> UnitRead:
    """Create a new unit in the system.

    Args:
        unit_data: Unit creation data containing name, type, and conversion factor.
        db: Database session dependency.

    Returns:
        The newly created unit with all its properties.

    Raises:
        HTTPException: 400 if unit name already exists.

    Example:
        ```json
        {
            "name": "kg",
            "type": "weight",
            "to_base_factor": 1000.0
        }
        ```
    """
    try:
        unit = crud_core.create_unit(db=db, unit_data=unit_data)
        return UnitRead.model_validate(unit, from_attributes=True)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit with name '{unit_data.name}' already exists"
        )


@units_router.get(
    "/",
    response_model=list[UnitRead],
    summary="Get all units"
)
def get_all_units(
    db: Annotated[Session, Depends(get_db)],
    unit_type: Annotated[UnitType | None, Query(description="Filter by unit type")] = None
) -> list[UnitRead]:
    """Retrieve all units, optionally filtered by type.

    Args:
        db: Database session dependency.
        unit_type: Optional filter to get units of a specific type only.

    Returns:
        List of all units matching the filter criteria.

    Example:
        - GET /units/ → Returns all units
        - GET /units/?unit_type=weight → Returns only weight units
    """
    units = crud_core.get_all_units(db=db, unit_type=unit_type)
    return [UnitRead.model_validate(unit, from_attributes=True) for unit in units]


@units_router.get(
    "/{unit_id}",
    response_model=UnitRead,
    summary="Get a single unit by ID"
)
def get_unit_by_id(
    unit_id: int,
    db: Annotated[Session, Depends(get_db)]
) -> UnitRead:
    """Retrieve a specific unit by its ID.

    Args:
        unit_id: The unique identifier of the unit to retrieve.
        db: Database session dependency.

    Returns:
        The requested unit with all its properties.

    Raises:
        HTTPException: 404 if unit with the specified ID is not found.
    """
    unit = crud_core.get_unit_by_id(db=db, unit_id=unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found"
        )
    return UnitRead.model_validate(unit, from_attributes=True)


@units_router.patch(
    "/{unit_id}",
    response_model=UnitRead,
    summary="Update an existing unit"
)
def update_unit(
    unit_id: int,
    unit_data: UnitUpdate,
    db: Annotated[Session, Depends(get_db)]
) -> UnitRead:
    """Update an existing unit with partial data.

    Args:
        unit_id: The unique identifier of the unit to update.
        unit_data: Partial unit data to update (only provided fields are updated).
        db: Database session dependency.

    Returns:
        The updated unit with all its properties.

    Raises:
        HTTPException: 
            - 404 if unit with the specified ID is not found.
            - 400 if updated name conflicts with existing unit.

    Example:
        ```json
        {
            "name": "kilogram",
            "to_base_factor": 1000.0
        }
        ```

    Note:
        All fields are optional. Only provided fields will be updated.
    """
    try:
        updated_unit = crud_core.update_unit(db=db, unit_id=unit_id, unit_data=unit_data)
        if not updated_unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unit with ID {unit_id} not found"
            )
        return UnitRead.model_validate(updated_unit, from_attributes=True)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit name '{unit_data.name}' already exists"
        )


@units_router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a unit"
)
def delete_unit(
    unit_id: int,
    db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete a unit from the system.

    Args:
        unit_id: The unique identifier of the unit to delete.
        db: Database session dependency.

    Returns:
        Empty response with 204 status code.

    Raises:
        HTTPException: 
            - 404 if unit with the specified ID is not found.
            - 400 if unit has dependent conversions and cannot be deleted.

    Note:
        Units with existing conversions cannot be deleted to maintain referential integrity.
        Delete all conversions referencing this unit first.
    """
    # Check if unit exists
    unit = crud_core.get_unit_by_id(db=db, unit_id=unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found"
        )

    # Check if unit has conversions
    if crud_core.has_unit_conversions(db=db, unit_id=unit_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete unit '{unit.name}' because it has dependent conversions. Delete conversions first."
        )

    success = crud_core.delete_unit(db=db, unit_id=unit_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete unit"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@units_router.get(
    "/{unit_id}/conversions",
    response_model=UnitWithConversions,
    summary="Get unit with available conversions"
)
def get_unit_conversions(
    unit_id: int,
    db: Annotated[Session, Depends(get_db)]
) -> UnitWithConversions:
    """Retrieve a unit along with all its available conversions to other units.

    Args:
        unit_id: The unique identifier of the unit.
        db: Database session dependency.

    Returns:
        Unit data including a list of all possible conversions from this unit.

    Raises:
        HTTPException: 404 if unit with the specified ID is not found.
    """
    unit = crud_core.get_unit_by_id(db=db, unit_id=unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found"
        )

    conversions = crud_core.get_conversions_from_unit(db=db, unit_id=unit_id)
    conversion_reads = [
        UnitConversionRead(
            from_unit_id=conv.from_unit_id,
            to_unit_id=conv.to_unit_id,
            factor=conv.factor,
            from_unit_name=conv.from_unit.name,
            to_unit_name=conv.to_unit.name
        )
        for conv in conversions
    ]

    return UnitWithConversions(
        **UnitRead.model_validate(unit, from_attributes=True).model_dump(),
        available_conversions=conversion_reads
    )


# ================================================================== #
# Unit Conversion Management Endpoints                               #
# ================================================================== #

@conversions_router.post(
    "/conversions/",
    response_model=UnitConversionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new unit conversion"
)
def create_unit_conversion(
    conversion_data: UnitConversionCreate,
    db: Annotated[Session, Depends(get_db)]
) -> UnitConversionRead:
    """Create a new conversion relationship between two units.

    Args:
        conversion_data: Conversion data containing source unit, target unit, and factor.
        db: Database session dependency.

    Returns:
        The newly created unit conversion with unit names included.

    Raises:
        HTTPException: 
            - 400 if conversion already exists or if source/target units don't exist.

    Example:
        ```json
        {
            "from_unit_id": 1,
            "to_unit_id": 2,
            "factor": 1000.0
        }
        ```
    """
    # Validate that both units exist
    from_unit = crud_core.get_unit_by_id(db=db, unit_id=conversion_data.from_unit_id)
    to_unit = crud_core.get_unit_by_id(db=db, unit_id=conversion_data.to_unit_id)

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
        conversion = crud_core.create_unit_conversion(db=db, conversion_data=conversion_data)
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


@conversions_router.get(
    "/conversions/",
    response_model=list[UnitConversionRead],
    summary="Get unit conversions with optional filtering"
)
def get_unit_conversions_filtered(
    db: Annotated[Session, Depends(get_db)],
    from_unit_id: Annotated[int | None, Query(description="Filter by source unit ID")] = None,
    to_unit_id: Annotated[int | None, Query(description="Filter by target unit ID")] = None
) -> list[UnitConversionRead]:
    """Retrieve unit conversions with optional filtering by source or target unit.

    Args:
        db: Database session dependency.
        from_unit_id: Optional filter to get conversions from a specific unit.
        to_unit_id: Optional filter to get conversions to a specific unit.

    Returns:
        List of unit conversions matching the filter criteria.

    Examples:
        - GET /units/conversions/ → All conversions
        - GET /units/conversions/?from_unit_id=1 → All conversions from unit 1
        - GET /units/conversions/?to_unit_id=2 → All conversions to unit 2
        - GET /units/conversions/?from_unit_id=1&to_unit_id=2 → Specific conversion
    """
    if from_unit_id and to_unit_id:
        # Get specific conversion
        conversion = crud_core.get_unit_conversion(
            db=db,
            from_unit_id=from_unit_id,
            to_unit_id=to_unit_id
        )
        conversions = [conversion] if conversion else []
    elif from_unit_id:
        # Get all conversions from a unit
        conversions = crud_core.get_conversions_from_unit(db=db, unit_id=from_unit_id)
    elif to_unit_id:
        # Get all conversions to a unit
        conversions = crud_core.get_conversions_to_unit(db=db, unit_id=to_unit_id)
    else:
        # Get all conversions
        conversions = crud_core.get_all_unit_conversions(db=db)

    return [
        UnitConversionRead(
            from_unit_id=conv.from_unit_id,
            to_unit_id=conv.to_unit_id,
            factor=conv.factor,
            from_unit_name=conv.from_unit.name,
            to_unit_name=conv.to_unit.name
        )
        for conv in conversions
    ]


@conversions_router.patch(
    "/conversions/{from_unit_id}/{to_unit_id}",
    response_model=UnitConversionRead,
    summary="Update a unit conversion factor"
)
def update_unit_conversion(
    from_unit_id: int,
    to_unit_id: int,
    conversion_data: UnitConversionUpdate,
    db: Annotated[Session, Depends(get_db)]
) -> UnitConversionRead:
    """Update the conversion factor for an existing unit conversion.

    Args:
        from_unit_id: Source unit identifier.
        to_unit_id: Target unit identifier.
        conversion_data: Updated conversion data (factor).
        db: Database session dependency.

    Returns:
        The updated unit conversion with unit names included.

    Raises:
        HTTPException: 404 if conversion is not found.

    Example:
        ```json
        {
            "factor": 1234.5
        }
        ```

    Note:
        Only the conversion factor can be updated. To change units, 
        delete the existing conversion and create a new one.
    """
    updated_conversion = crud_core.update_unit_conversion(
        db=db,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id,
        conversion_data=conversion_data
    )
    
    if not updated_conversion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion from unit {from_unit_id} to unit {to_unit_id} not found"
        )

    return UnitConversionRead(
        from_unit_id=updated_conversion.from_unit_id,
        to_unit_id=updated_conversion.to_unit_id,
        factor=updated_conversion.factor,
        from_unit_name=updated_conversion.from_unit.name,
        to_unit_name=updated_conversion.to_unit.name
    )


@conversions_router.delete(
    "/conversions/{from_unit_id}/{to_unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a unit conversion"
)
def delete_unit_conversion(
    from_unit_id: int,
    to_unit_id: int,
    db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete a unit conversion relationship.

    Args:
        from_unit_id: Source unit identifier.
        to_unit_id: Target unit identifier.
        db: Database session dependency.

    Returns:
        Empty response with 204 status code.

    Raises:
        HTTPException: 404 if conversion is not found.

    Example:
        DELETE /units/conversions/1/2
        Deletes the conversion from unit 1 to unit 2.
    """
    success = crud_core.delete_unit_conversion(
        db=db,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion from unit {from_unit_id} to unit {to_unit_id} not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Unit Conversion Calculation Endpoints                              #
# ================================================================== #

@conversions_router.post(
    "/{from_unit_id}/convert-to/{to_unit_id}",
    response_model=ConversionResult,
    summary="Convert value between units"
)
def convert_value_between_units(
    from_unit_id: int,
    to_unit_id: int,
    value: Annotated[float, Query(description="Value to convert", gt=0)],
    db: Annotated[Session, Depends(get_db)]
) -> ConversionResult:
    """Convert a value from one unit to another.

    Args:
        from_unit_id: Source unit ID for the conversion.
        to_unit_id: Target unit ID for the conversion.
        value: The numeric value to convert (must be positive).
        db: Database session dependency.

    Returns:
        Complete conversion result with original and converted values.

    Raises:
        HTTPException: 
            - 400 if units don't exist or conversion is not possible.
            - 404 if either unit is not found.

    Example:
        POST /units/1/convert-to/2?value=123.45
    """
    # Validate that both units exist
    from_unit = crud_core.get_unit_by_id(db=db, unit_id=from_unit_id)
    to_unit = crud_core.get_unit_by_id(db=db, unit_id=to_unit_id)

    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source unit with ID {from_unit_id} not found"
        )

    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target unit with ID {to_unit_id} not found"
        )

    # Perform conversion
    converted_value = crud_core.convert_value(
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
    factor = 1.0 if from_unit_id == to_unit_id else crud_core.get_conversion_factor(
        db=db, from_unit_id=from_unit_id, to_unit_id=to_unit_id
    )

    return ConversionResult(
        original_value=value,
        original_unit_id=from_unit_id,
        original_unit_name=from_unit.name,
        converted_value=converted_value,
        target_unit_id=to_unit_id,
        target_unit_name=to_unit.name,
        conversion_factor=factor
    )


@conversions_router.get(
    "/{from_unit_id}/can-convert-to/{to_unit_id}",
    summary="Check if conversion between units is possible"
)
def check_conversion_possibility(
    from_unit_id: int,
    to_unit_id: int,
    db: Annotated[Session, Depends(get_db)]
) -> dict[str, bool]:
    """Check if conversion between two units is possible.

    Args:
        from_unit_id: Source unit ID.
        to_unit_id: Target unit ID.
        db: Database session dependency.

    Returns:
        Dictionary indicating whether the conversion is possible.

    Example:
        GET /units/1/can-convert-to/2
        Returns: {"can_convert": true}
    """
    can_convert = crud_core.can_convert_units(
        db=db,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )

    return {"can_convert": can_convert}


# ================================================================== #
# Combined Router                                                     #
# ================================================================== #

# Create main router that includes both sub-routers
router = APIRouter()
router.include_router(units_router)
router.include_router(conversions_router)
