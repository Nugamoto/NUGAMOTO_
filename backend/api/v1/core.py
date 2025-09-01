"""API endpoints for core unit system."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db, get_current_user_id, require_super_admin
from backend.core.enums import UnitType
from backend.crud import core as crud_core
from backend.schemas.core import (
    ConversionResult,
    UnitConversionCreate,
    UnitConversionRead,
    UnitConversionUpdate,
    UnitCreate,
    UnitRead,
    UnitUpdate,
    UnitWithConversions,
)

# ================================================================== #
# Sub-routers for better organization                               #
# ================================================================== #

units_router = APIRouter(prefix="/units", tags=["Unit Management"])
conversions_router = APIRouter(prefix="/units", tags=["Unit Conversion"])


# ================================================================== #
# Unit Management Endpoints                                          #
# ================================================================== #

@units_router.post(
    "/",
    response_model=UnitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new unit",
    dependencies=[Depends(get_current_user_id)],  # any authenticated user can create
)
def create_unit(
    unit_data: UnitCreate,
        db: Annotated[Session, Depends(get_db)],
) -> UnitRead:
    """Create a new unit in the system."""
    try:
        return crud_core.create_unit(db=db, unit_data=unit_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit with name '{unit_data.name}' already exists",
        )


@units_router.get(
    "/",
    response_model=list[UnitRead],
    summary="Get all units",
    dependencies=[Depends(get_current_user_id)],  # any authenticated user can read
)
def get_all_units(
    db: Annotated[Session, Depends(get_db)],
        unit_type: Annotated[UnitType | None, Query(description="Filter by unit type")] = None,
) -> list[UnitRead]:
    """Retrieve all units, optionally filtered by type."""
    return crud_core.get_all_units(db=db, unit_type=unit_type)


@units_router.get(
    "/{unit_id}",
    response_model=UnitRead,
    summary="Get a single unit by ID",
    dependencies=[Depends(get_current_user_id)],  # any authenticated user can read
)
def get_unit_by_id(
    unit_id: int,
        db: Annotated[Session, Depends(get_db)],
) -> UnitRead:
    """Retrieve a specific unit by its ID."""
    unit = crud_core.get_unit_by_id(db=db, unit_id=unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found",
        )
    return unit


@units_router.patch(
    "/{unit_id}",
    response_model=UnitRead,
    summary="Update an existing unit",
    dependencies=[Depends(require_super_admin)],  # only admins can update
)
def update_unit(
    unit_id: int,
    unit_data: UnitUpdate,
        db: Annotated[Session, Depends(get_db)],
) -> UnitRead:
    """Update an existing unit with partial data."""
    try:
        updated_unit = crud_core.update_unit(db=db, unit_id=unit_id, unit_data=unit_data)
        if not updated_unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unit with ID {unit_id} not found",
            )
        return updated_unit
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unit name '{unit_data.name}' already exists",
        )


@units_router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a unit",
    dependencies=[Depends(require_super_admin)],  # only admins can delete
)
def delete_unit(
    unit_id: int,
        db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Delete a unit from the system."""
    # Check if unit exists
    unit = crud_core.get_unit_by_id(db=db, unit_id=unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found",
        )

    # Check if unit has conversions
    if crud_core.has_unit_conversions(db=db, unit_id=unit_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete unit '{unit.name}' because it has dependent conversions. Delete conversions first.",
        )

    success = crud_core.delete_unit(db=db, unit_id=unit_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete unit",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@units_router.get(
    "/{unit_id}/conversions",
    response_model=UnitWithConversions,
    summary="Get unit with available conversions",
    dependencies=[Depends(get_current_user_id)],  # any authenticated user can read
)
def get_unit_conversions(
    unit_id: int,
        db: Annotated[Session, Depends(get_db)],
) -> UnitWithConversions:
    """Retrieve a unit along with all its available conversions to other units."""
    unit_with_conversions = crud_core.get_unit_with_conversions(db=db, unit_id=unit_id)
    if not unit_with_conversions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit with ID {unit_id} not found",
        )
    return unit_with_conversions


# ================================================================== #
# Unit Conversion Management Endpoints                               #
# ================================================================== #

@conversions_router.post(
    "/conversions/",
    response_model=UnitConversionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new unit conversion",
    dependencies=[Depends(get_current_user_id)],  # any authenticated user can create
)
def create_unit_conversion(
    conversion_data: UnitConversionCreate,
        db: Annotated[Session, Depends(get_db)],
) -> UnitConversionRead:
    """Create a new conversion relationship between two units."""
    # Validate that both units exist
    from_unit = crud_core.get_unit_by_id(db=db, unit_id=conversion_data.from_unit_id)
    to_unit = crud_core.get_unit_by_id(db=db, unit_id=conversion_data.to_unit_id)

    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source unit with ID {conversion_data.from_unit_id} not found",
        )

    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target unit with ID {conversion_data.to_unit_id} not found",
        )

    try:
        return crud_core.create_unit_conversion(db=db, conversion_data=conversion_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Conversion from unit {conversion_data.from_unit_id} "
                f"to unit {conversion_data.to_unit_id} already exists"
            ),
        )


@conversions_router.get(
    "/conversions/",
    response_model=list[UnitConversionRead],
    summary="Get unit conversions with optional filtering",
    dependencies=[Depends(get_current_user_id)],  # any authenticated user can read
)
def get_unit_conversions_filtered(
    db: Annotated[Session, Depends(get_db)],
    from_unit_id: Annotated[int | None, Query(description="Filter by source unit ID")] = None,
        to_unit_id: Annotated[int | None, Query(description="Filter by target unit ID")] = None,
) -> list[UnitConversionRead]:
    """Retrieve unit conversions with optional filtering by source or target unit."""
    if from_unit_id and to_unit_id:
        # Get specific conversion
        conversion = crud_core.get_unit_conversion(
            db=db, from_unit_id=from_unit_id, to_unit_id=to_unit_id
        )
        return [conversion] if conversion else []
    elif from_unit_id:
        # Get all conversions from a unit
        return crud_core.get_conversions_from_unit(db=db, unit_id=from_unit_id)
    elif to_unit_id:
        # Get all conversions to a unit
        return crud_core.get_conversions_to_unit(db=db, unit_id=to_unit_id)
    else:
        # Get all conversions
        return crud_core.get_all_unit_conversions(db=db)


@conversions_router.patch(
    "/conversions/{from_unit_id}/{to_unit_id}",
    response_model=UnitConversionRead,
    summary="Update a unit conversion factor",
    dependencies=[Depends(require_super_admin)],  # only admins can update
)
def update_unit_conversion(
    from_unit_id: int,
    to_unit_id: int,
    conversion_data: UnitConversionUpdate,
        db: Annotated[Session, Depends(get_db)],
) -> UnitConversionRead:
    """Update the conversion factor for an existing unit conversion."""
    updated_conversion = crud_core.update_unit_conversion(
        db=db, from_unit_id=from_unit_id, to_unit_id=to_unit_id, conversion_data=conversion_data
    )

    if not updated_conversion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion from unit {from_unit_id} to unit {to_unit_id} not found",
        )

    return updated_conversion


@conversions_router.delete(
    "/conversions/{from_unit_id}/{to_unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a unit conversion",
    dependencies=[Depends(require_super_admin)],  # only admins can delete
)
def delete_unit_conversion(
    from_unit_id: int,
    to_unit_id: int,
        db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Delete a unit conversion relationship."""
    success = crud_core.delete_unit_conversion(db=db, from_unit_id=from_unit_id, to_unit_id=to_unit_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion from unit {from_unit_id} to unit {to_unit_id} not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Unit Conversion Calculation Endpoints                              #
# ================================================================== #

@conversions_router.post(
    "/{from_unit_id}/convert-to/{to_unit_id}",
    response_model=ConversionResult,
    summary="Convert value between units",
    dependencies=[Depends(get_current_user_id)],  # any authenticated user can convert
)
def convert_value_between_units(
    from_unit_id: int,
    to_unit_id: int,
    value: Annotated[float, Query(description="Value to convert", gt=0)],
        db: Annotated[Session, Depends(get_db)],
) -> ConversionResult:
    """Convert a value from one unit to another."""
    # Validate that both units exist
    from_unit = crud_core.get_unit_by_id(db=db, unit_id=from_unit_id)
    to_unit = crud_core.get_unit_by_id(db=db, unit_id=to_unit_id)

    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source unit with ID {from_unit_id} not found",
        )

    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target unit with ID {to_unit_id} not found",
        )

    # Perform conversion
    converted_value = crud_core.convert_value(
        db=db, value=value, from_unit_id=from_unit_id, to_unit_id=to_unit_id
    )

    if converted_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No conversion available from '{from_unit.name}' to '{to_unit.name}'",
        )

    # Calculate the conversion factor used
    factor = (
        1.0
        if from_unit_id == to_unit_id
        else crud_core.get_conversion_factor(db=db, from_unit_id=from_unit_id, to_unit_id=to_unit_id)
    )

    return crud_core.create_conversion_result(
        db=db,
        original_value=value,
        converted_value=converted_value,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id,
        conversion_factor=factor or 1.0,
    )


@conversions_router.get(
    "/{from_unit_id}/can-convert-to/{to_unit_id}",
    summary="Check if conversion between units is possible",
    dependencies=[Depends(get_current_user_id)],  # any authenticated user can check
)
def check_conversion_possibility(
    from_unit_id: int,
    to_unit_id: int,
        db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    """Check if conversion between two units is possible."""
    can_convert = crud_core.can_convert_units(db=db, from_unit_id=from_unit_id, to_unit_id=to_unit_id)
    return {"can_convert": can_convert}


# ================================================================== #
# Main Router Assembly                                               #
# ================================================================== #
router = APIRouter()

# Include all sub-routers
router.include_router(units_router)
router.include_router(conversions_router)