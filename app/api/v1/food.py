"""API endpoints for food system."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import core as crud_core
from app.crud import food as crud_food
from app.schemas.food import (
    FoodConversionResult,
    FoodItemCreate,
    FoodItemRead,
    FoodItemUpdate,
    FoodItemUnitConversionCreate,
    FoodItemUnitConversionRead,
    FoodItemWithConversions
)

router = APIRouter()


# ================================================================== #
# FoodItem Endpoints                                                 #
# ================================================================== #

@router.post("/food-items/", response_model=FoodItemRead, status_code=status.HTTP_201_CREATED)
def create_food_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_data: FoodItemCreate
) -> FoodItemRead:
    """Create a new food item.

    Args:
        db: Database session
        food_item_data: Food item creation data

    Returns:
        Created food item data

    Raises:
        HTTPException: 400 if food item name already exists or base_unit_id doesn't exist
    """
    # Validate that base_unit exists
    base_unit = crud_core.get_unit_by_id(db=db, unit_id=food_item_data.base_unit_id)
    if not base_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Base unit with ID {food_item_data.base_unit_id} not found"
        )

    try:
        food_item = crud_food.create_food_item(db=db, food_item_data=food_item_data)
        return FoodItemRead(
            **food_item.__dict__,
            base_unit_name=base_unit.name
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with name '{food_item_data.name}' already exists"
        )


@router.get("/food-items/", response_model=list[FoodItemRead])
def get_food_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        category: Annotated[str | None, Query(description="Filter by category")] = None,
        skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
        limit: Annotated[int, Query(ge=1, le=1000, description="Maximum number of items to return")] = 100
) -> list[FoodItemRead]:
    """Get all food items with optional filtering.

    Args:
        db: Database session
        category: Optional category filter
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of food items
    """
    food_items = crud_food.get_all_food_items(
        db=db,
        category=category,
        skip=skip,
        limit=limit
    )

    result = []
    for food_item in food_items:
        result.append(FoodItemRead(
            **food_item.__dict__,
            base_unit_name=food_item.base_unit.name if food_item.base_unit else None
        ))

    return result


@router.get("/food-items/{food_item_id}", response_model=FoodItemRead)
def get_food_item_by_id(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int
) -> FoodItemRead:
    """Get food item by ID.

    Args:
        db: Database session
        food_item_id: Food item ID to fetch

    Returns:
        Food item data

    Raises:
        HTTPException: 404 if food item not found
    """
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food item with ID {food_item_id} not found"
        )

    return FoodItemRead(
        **food_item.__dict__,
        base_unit_name=food_item.base_unit.name if food_item.base_unit else None
    )


@router.patch("/food-items/{food_item_id}", response_model=FoodItemRead)
def update_food_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        food_item_data: FoodItemUpdate
) -> FoodItemRead:
    """Update a food item.

    Args:
        db: Database session
        food_item_id: Food item ID to update
        food_item_data: Updated food item data

    Returns:
        Updated food item data

    Raises:
        HTTPException: 404 if food item not found, 400 if base_unit_id doesn't exist
    """
    # Validate base_unit_id if provided
    if food_item_data.base_unit_id is not None:
        base_unit = crud_core.get_unit_by_id(db=db, unit_id=food_item_data.base_unit_id)
        if not base_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Base unit with ID {food_item_data.base_unit_id} not found"
            )

    updated_food_item = crud_food.update_food_item(
        db=db,
        food_item_id=food_item_id,
        food_item_data=food_item_data
    )
    if not updated_food_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food item with ID {food_item_id} not found"
        )

    return FoodItemRead(
        **updated_food_item.__dict__,
        base_unit_name=updated_food_item.base_unit.name if updated_food_item.base_unit else None
    )


@router.delete("/food-items/{food_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int
) -> Response:
    """Delete a food item.

    Args:
        db: Database session
        food_item_id: Food item ID to delete

    Raises:
        HTTPException: 404 if food item not found
    """
    success = crud_food.delete_food_item(db=db, food_item_id=food_item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food item with ID {food_item_id} not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/food-items/{food_item_id}/with-conversions", response_model=FoodItemWithConversions)
def get_food_item_with_conversions(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int
) -> FoodItemWithConversions:
    """Get food item with available unit conversions.

    Args:
        db: Database session
        food_item_id: Food item ID to fetch

    Returns:
        Food item data with available unit conversions

    Raises:
        HTTPException: 404 if food item not found
    """
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food item with ID {food_item_id} not found"
        )

    conversions = crud_food.get_conversions_for_food_item(db=db, food_item_id=food_item_id)
    conversion_reads = []

    for conversion in conversions:
        conversion_reads.append(FoodItemUnitConversionRead(
            food_item_id=conversion.food_item_id,
            from_unit_id=conversion.from_unit_id,
            to_unit_id=conversion.to_unit_id,
            factor=conversion.factor,
            created_at=conversion.created_at,
            food_item_name=conversion.food_item.name,
            from_unit_name=conversion.from_unit.name,
            to_unit_name=conversion.to_unit.name
        ))

    return FoodItemWithConversions(
        **FoodItemRead(
            **food_item.__dict__,
            base_unit_name=food_item.base_unit.name if food_item.base_unit else None
        ).model_dump(),
        unit_conversions=conversion_reads
    )


# ================================================================== #
# FoodItemUnitConversion Endpoints                                   #
# ================================================================== #

@router.post(
    "/food-items/{food_item_id}/unit-conversions/",
    response_model=FoodItemUnitConversionRead,
    status_code=status.HTTP_201_CREATED
)
def create_food_unit_conversion(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        conversion_data: FoodItemUnitConversionCreate
) -> FoodItemUnitConversionRead:
    """Create a new unit conversion for a food item.

    Args:
        db: Database session
        food_item_id: Food item ID (must match conversion_data.food_item_id)
        conversion_data: Unit conversion creation data

    Returns:
        Created unit conversion data

    Raises:
        HTTPException: 400 if conversion already exists or entities don't exist
    """
    # Validate that food_item_id matches
    if conversion_data.food_item_id != food_item_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Food item ID in URL must match food_item_id in request body"
        )

    # Validate that entities exist
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with ID {food_item_id} not found"
        )

    from_unit = crud_core.get_unit_by_id(db=db, unit_id=conversion_data.from_unit_id)
    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source unit with ID {conversion_data.from_unit_id} not found"
        )

    to_unit = crud_core.get_unit_by_id(db=db, unit_id=conversion_data.to_unit_id)
    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target unit with ID {conversion_data.to_unit_id} not found"
        )

    try:
        conversion = crud_food.create_food_unit_conversion(db=db, conversion_data=conversion_data)
        return FoodItemUnitConversionRead(
            food_item_id=conversion.food_item_id,
            from_unit_id=conversion.from_unit_id,
            to_unit_id=conversion.to_unit_id,
            factor=conversion.factor,
            created_at=conversion.created_at,
            food_item_name=food_item.name,
            from_unit_name=from_unit.name,
            to_unit_name=to_unit.name
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversion for food item {food_item_id} from unit {conversion_data.from_unit_id} to unit {conversion_data.to_unit_id} already exists"
        )


@router.get(
    "/food-items/{food_item_id}/unit-conversions/",
    response_model=list[FoodItemUnitConversionRead]
)
def get_food_unit_conversions(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int
) -> list[FoodItemUnitConversionRead]:
    """Get all unit conversions for a food item.

    Args:
        db: Database session
        food_item_id: Food item ID

    Returns:
        List of unit conversions for the food item
    """
    conversions = crud_food.get_conversions_for_food_item(db=db, food_item_id=food_item_id)

    result = []
    for conversion in conversions:
        result.append(FoodItemUnitConversionRead(
            food_item_id=conversion.food_item_id,
            from_unit_id=conversion.from_unit_id,
            to_unit_id=conversion.to_unit_id,
            factor=conversion.factor,
            created_at=conversion.created_at,
            food_item_name=conversion.food_item.name,
            from_unit_name=conversion.from_unit.name,
            to_unit_name=conversion.to_unit.name
        ))

    return result


@router.delete(
    "/food-items/{food_item_id}/unit-conversions/{from_unit_id}/{to_unit_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_food_unit_conversion(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> Response:
    """Delete a unit conversion for a food item.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Raises:
        HTTPException: 404 if conversion not found
    """
    success = crud_food.delete_food_unit_conversion(
        db=db,
        food_item_id=food_item_id,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversion for food item {food_item_id} from unit {from_unit_id} to unit {to_unit_id} not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Food-Specific Conversion Endpoints                                 #
# ================================================================== #

@router.post("/food-items/{food_item_id}/convert/", response_model=FoodConversionResult)
def convert_food_units(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        value: Annotated[float, Query(description="Value to convert", gt=0)],
        from_unit_id: Annotated[int, Query(description="Source unit ID")],
        to_unit_id: Annotated[int, Query(description="Target unit ID")]
) -> FoodConversionResult:
    """Convert a value for a specific food item between units.

    This endpoint prioritizes food-specific conversions over generic unit conversions.

    Args:
        db: Database session
        food_item_id: Food item ID
        value: Value to convert
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Conversion result with original and converted values

    Raises:
        HTTPException: 400 if entities don't exist or conversion is not possible
    """
    # Validate that entities exist
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with ID {food_item_id} not found"
        )

    from_unit = crud_core.get_unit_by_id(db=db, unit_id=from_unit_id)
    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source unit with ID {from_unit_id} not found"
        )

    to_unit = crud_core.get_unit_by_id(db=db, unit_id=to_unit_id)
    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target unit with ID {to_unit_id} not found"
        )

    # Perform conversion
    conversion_result = crud_food.convert_food_value(
        db=db,
        food_item_id=food_item_id,
        value=value,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )

    if conversion_result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No conversion available for {food_item.name} from '{from_unit.name}' to '{to_unit.name}'"
        )

    converted_value, is_food_specific = conversion_result

    # Calculate the conversion factor used
    if from_unit_id == to_unit_id:
        factor = 1.0
    else:
        if is_food_specific:
            factor = crud_food.get_conversion_for_food_item(
                db=db,
                food_item_id=food_item_id,
                from_unit_id=from_unit_id,
                to_unit_id=to_unit_id
            )
        else:
            factor = crud_core.get_conversion_factor(
                db=db,
                from_unit_id=from_unit_id,
                to_unit_id=to_unit_id
            )

    return FoodConversionResult(
        food_item_id=food_item_id,
        food_item_name=food_item.name,
        original_value=value,
        original_unit_id=from_unit_id,
        original_unit_name=from_unit.name,
        converted_value=converted_value,
        target_unit_id=to_unit_id,
        target_unit_name=to_unit.name,
        conversion_factor=factor,
        is_food_specific=is_food_specific
    )


@router.get("/food-items/{food_item_id}/can-convert/")
def can_convert_food_units(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        from_unit_id: Annotated[int, Query(description="Source unit ID")],
        to_unit_id: Annotated[int, Query(description="Target unit ID")]
) -> dict[str, bool]:
    """Check if conversion between two units is possible for a specific food item.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Dictionary with conversion possibility status
    """
    can_convert = crud_food.can_convert_food_units(
        db=db,
        food_item_id=food_item_id,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )

    return {"can_convert": can_convert}
