"""API endpoints for food system."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import core as crud_core
from app.crud import food as crud_food
from app.schemas.food import (
    FoodItemCreate, FoodItemRead, FoodItemUpdate, FoodItemWithConversions,
    FoodItemUnitConversionCreate, FoodItemUnitConversionRead,
    FoodItemAliasCreate, FoodItemAliasRead, FoodItemWithAliases,
    FoodConversionResult
)

router = APIRouter(prefix="/food-items", tags=["Food Items"])


# ================================================================== #
# FoodItem Endpoints                                                 #
# ================================================================== #

@router.post("/", response_model=FoodItemRead, status_code=status.HTTP_201_CREATED)
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


@router.get("/", response_model=list[FoodItemRead])
def get_food_items(
        *,
        db: Annotated[Session, Depends(get_db)],
        category: str | None = None,
        skip: int = 0,
        limit: int = 100
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
        db=db, category=category, skip=skip, limit=limit
    )

    return [
        FoodItemRead(
            **food_item.__dict__,
            base_unit_name=food_item.base_unit.name if food_item.base_unit else None
        )
        for food_item in food_items
    ]


@router.get("/{food_item_id}", response_model=FoodItemRead)
def get_food_item_by_id(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int
) -> FoodItemRead:
    """Get food item by ID.

    Args:
        db: Database session
        food_item_id: Food item ID

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


@router.patch("/{food_item_id}", response_model=FoodItemRead)
def update_food_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        food_item_data: FoodItemUpdate
) -> FoodItemRead:
    """Update an existing food item.

    Args:
        db: Database session
        food_item_id: Food item ID
        food_item_data: Updated food item data

    Returns:
        Updated food item data

    Raises:
        HTTPException: 404 if food item not found, 400 if base_unit_id doesn't exist
    """
    # Validate base_unit if provided
    if food_item_data.base_unit_id is not None:
        base_unit = crud_core.get_unit_by_id(db=db, unit_id=food_item_data.base_unit_id)
        if not base_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Base unit with ID {food_item_data.base_unit_id} not found"
            )

    try:
        food_item = crud_food.update_food_item(
            db=db, food_item_id=food_item_id, food_item_data=food_item_data
        )
        if not food_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Food item with ID {food_item_id} not found"
            )

        return FoodItemRead(
            **food_item.__dict__,
            base_unit_name=food_item.base_unit.name if food_item.base_unit else None
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with name '{food_item_data.name}' already exists"
        )


@router.delete("/{food_item_id}")
def delete_food_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int
) -> Response:
    """Delete a food item.

    Args:
        db: Database session
        food_item_id: Food item ID

    Returns:
        Empty response with 204 status

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


@router.get("/{food_item_id}/with-conversions", response_model=FoodItemWithConversions)
def get_food_item_with_conversions(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int
) -> FoodItemWithConversions:
    """Get food item with its unit conversions.

    Args:
        db: Database session
        food_item_id: Food item ID

    Returns:
        Food item data with unit conversions

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

    conversion_reads = [
        FoodItemUnitConversionRead(
            **conversion.__dict__,
            food_item_name=food_item.name,
            from_unit_name=conversion.from_unit.name if conversion.from_unit else None,
            to_unit_name=conversion.to_unit.name if conversion.to_unit else None
        )
        for conversion in conversions
    ]

    return FoodItemWithConversions(
        **food_item.__dict__,
        base_unit_name=food_item.base_unit.name if food_item.base_unit else None,
        unit_conversions=conversion_reads
    )


# ================================================================== #
# FoodItemAlias Endpoints                                            #
# ================================================================== #

@router.post("/{food_item_id}/aliases/", response_model=FoodItemAliasRead, status_code=status.HTTP_201_CREATED)
def create_food_item_alias(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        alias_data: FoodItemAliasCreate
) -> FoodItemAliasRead:
    """Create a new alias for a food item.

    Args:
        db: Database session
        food_item_id: Food item ID (from URL path)
        alias_data: Alias creation data

    Returns:
        Created alias data

    Raises:
        HTTPException: 400 if food item doesn't exist or alias already exists
        HTTPException: 422 if food_item_id in body doesn't match URL parameter
    """
    # Ensure the food_item_id in the request body matches the URL parameter
    if alias_data.food_item_id != food_item_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Food item ID in body ({alias_data.food_item_id}) must match URL parameter ({food_item_id})"
        )

    # Validate that food_item exists
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with ID {food_item_id} not found"
        )

    # Validate user if provided
    if alias_data.user_id is not None:
        from app.crud import user as crud_user
        user = crud_user.get_user_by_id(db=db, user_id=alias_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with ID {alias_data.user_id} not found"
            )

    try:
        alias = crud_food.create_food_item_alias(db=db, alias_data=alias_data)
        return FoodItemAliasRead(
            **alias.__dict__,
            food_item_name=food_item.name,
            user_name=alias.user.name if alias.user else None
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alias '{alias_data.alias}' already exists for this food item and user combination"
        )


@router.get("/{food_item_id}/aliases/", response_model=list[FoodItemAliasRead])
def get_aliases_for_food_item(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        user_id: int | None = None
) -> list[FoodItemAliasRead]:
    """Get all aliases for a specific food item.

    Args:
        db: Database session
        food_item_id: Food item ID
        user_id: Optional user ID to filter user-specific aliases

    Returns:
        List of aliases for the food item

    Raises:
        HTTPException: 404 if food item not found
    """
    # Validate that food_item exists
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food item with ID {food_item_id} not found"
        )

    aliases = crud_food.get_aliases_for_food_item(
        db=db, food_item_id=food_item_id, user_id=user_id
    )

    return [
        FoodItemAliasRead(
            **alias.__dict__,
            food_item_name=food_item.name,
            user_name=alias.user.name if alias.user else None
        )
        for alias in aliases
    ]


@router.get("/{food_item_id}/with-aliases", response_model=FoodItemWithAliases)
def get_food_item_with_aliases(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        user_id: int | None = None
) -> FoodItemWithAliases:
    """Get food item with its aliases.

    Args:
        db: Database session
        food_item_id: Food item ID
        user_id: Optional user ID to include user-specific aliases

    Returns:
        Food item data with aliases

    Raises:
        HTTPException: 404 if food item not found
    """
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food item with ID {food_item_id} not found"
        )

    aliases = crud_food.get_aliases_for_food_item(
        db=db, food_item_id=food_item_id, user_id=user_id
    )

    alias_reads = [
        FoodItemAliasRead(
            **alias.__dict__,
            food_item_name=food_item.name,
            user_name=alias.user.name if alias.user else None
        )
        for alias in aliases
    ]

    return FoodItemWithAliases(
        **food_item.__dict__,
        base_unit_name=food_item.base_unit.name if food_item.base_unit else None,
        aliases=alias_reads
    )


# ================================================================== #
# User-specific Alias Endpoints                                     #
# ================================================================== #

@router.get("/users/{user_id}/food-aliases/", response_model=list[FoodItemAliasRead])
def get_all_aliases_for_user(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[FoodItemAliasRead]:
    """Get all aliases created by a specific user.

    Args:
        db: Database session
        user_id: User ID
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        List of aliases created by the user

    Raises:
        HTTPException: 404 if user not found
    """
    # Validate that user exists
    from app.crud import user as crud_user
    user = crud_user.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )

    aliases = crud_food.get_all_aliases_for_user(
        db=db, user_id=user_id, skip=skip, limit=limit
    )

    return [
        FoodItemAliasRead(
            **alias.__dict__,
            food_item_name=alias.food_item.name if alias.food_item else None,
            user_name=user.name
        )
        for alias in aliases
    ]


@router.delete("/food-aliases/{alias_id}")
def delete_alias_by_id(
        *,
        db: Annotated[Session, Depends(get_db)],
        alias_id: int
) -> Response:
    """Delete an alias by ID.

    Args:
        db: Database session
        alias_id: Alias ID

    Returns:
        Empty response with 204 status

    Raises:
        HTTPException: 404 if alias not found
    """
    success = crud_food.delete_alias_by_id(db=db, alias_id=alias_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alias with ID {alias_id} not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Search Endpoints                                                   #
# ================================================================== #

@router.get("/search/by-alias", response_model=list[FoodItemRead])
def search_food_items_by_alias(
        *,
        db: Annotated[Session, Depends(get_db)],
        alias_term: str,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[FoodItemRead]:
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
    food_items = crud_food.search_food_items_by_alias(
        db=db, alias_term=alias_term, user_id=user_id, skip=skip, limit=limit
    )

    return [
        FoodItemRead(
            **food_item.__dict__,
            base_unit_name=food_item.base_unit.name if food_item.base_unit else None
        )
        for food_item in food_items
    ]


# ================================================================== #
# Unit Conversion Endpoints                                          #
# ================================================================== #

@router.post("/unit-conversions/", response_model=FoodItemUnitConversionRead, status_code=status.HTTP_201_CREATED)
def create_food_unit_conversion(
        *,
        db: Annotated[Session, Depends(get_db)],
        conversion_data: FoodItemUnitConversionCreate
) -> FoodItemUnitConversionRead:
    """Create a new food item unit conversion.

    Args:
        db: Database session
        conversion_data: Unit conversion creation data

    Returns:
        Created unit conversion data

    Raises:
        HTTPException: 400 if food item, units don't exist or conversion already exists
    """
    # Validate food item exists
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=conversion_data.food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with ID {conversion_data.food_item_id} not found"
        )

    # Validate units exist
    from_unit = crud_core.get_unit_by_id(db=db, unit_id=conversion_data.from_unit_id)
    to_unit = crud_core.get_unit_by_id(db=db, unit_id=conversion_data.to_unit_id)

    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"From unit with ID {conversion_data.from_unit_id} not found"
        )
    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"To unit with ID {conversion_data.to_unit_id} not found"
        )

    try:
        conversion = crud_food.create_food_unit_conversion(db=db, conversion_data=conversion_data)
        return FoodItemUnitConversionRead(
            **conversion.__dict__,
            food_item_name=food_item.name,
            from_unit_name=from_unit.name,
            to_unit_name=to_unit.name
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unit conversion from {from_unit.name} to {to_unit.name} "
                f"already exists for food item '{food_item.name}'"
            )
        )


@router.get("/{food_item_id}/unit-conversions/", response_model=list[FoodItemUnitConversionRead])
def get_food_unit_conversions(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int
) -> list[FoodItemUnitConversionRead]:
    """Get all unit conversions for a specific food item.

    Args:
        db: Database session
        food_item_id: Food item ID

    Returns:
        List of unit conversions for the food item

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

    return [
        FoodItemUnitConversionRead(
            **conversion.__dict__,
            food_item_name=food_item.name,
            from_unit_name=conversion.from_unit.name if conversion.from_unit else None,
            to_unit_name=conversion.to_unit.name if conversion.to_unit else None
        )
        for conversion in conversions
    ]


@router.delete("/{food_item_id}/unit-conversions/{from_unit_id}/{to_unit_id}")
def delete_food_unit_conversion(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> Response:
    """Delete a food item unit conversion.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Empty response with 204 status

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
            detail=f"Unit conversion not found for food item {food_item_id}"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Conversion Calculation Endpoints                                   #
# ================================================================== #

@router.post("/{food_item_id}/convert", response_model=FoodConversionResult)
def convert_food_units(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        value: float,
        from_unit_id: int,
        to_unit_id: int
) -> FoodConversionResult:
    """Convert a value for a specific food item between units.

    Args:
        db: Database session
        food_item_id: Food item ID
        value: Value to convert
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        Conversion result with details

    Raises:
        HTTPException: 400 if food item or units don't exist
        HTTPException: 422 if conversion is not possible
    """
    # Validate food item exists
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with ID {food_item_id} not found"
        )

    # Validate units exist
    from_unit = crud_core.get_unit_by_id(db=db, unit_id=from_unit_id)
    to_unit = crud_core.get_unit_by_id(db=db, unit_id=to_unit_id)

    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"From unit with ID {from_unit_id} not found"
        )
    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"To unit with ID {to_unit_id} not found"
        )

    # Perform conversion
    result = crud_food.convert_food_value(
        db=db,
        food_item_id=food_item_id,
        value=value,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot convert from {from_unit.name} to {to_unit.name} for {food_item.name}"
        )

    converted_value, is_food_specific = result
    factor = converted_value / value if value != 0 else 1.0

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


@router.get("/{food_item_id}/can-convert/{from_unit_id}/{to_unit_id}")
def can_convert_food_units(
        *,
        db: Annotated[Session, Depends(get_db)],
        food_item_id: int,
        from_unit_id: int,
        to_unit_id: int
) -> dict[str, bool]:
    """Check if conversion between two units is possible for a specific food item.

    Args:
        db: Database session
        food_item_id: Food item ID
        from_unit_id: Source unit ID
        to_unit_id: Target unit ID

    Returns:
        True if conversion is possible, False otherwise

    Raises:
        HTTPException: 400 if food item or units don't exist
    """
    # Validate food item exists
    food_item = crud_food.get_food_item_by_id(db=db, food_item_id=food_item_id)
    if not food_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Food item with ID {food_item_id} not found"
        )

    # Validate units exist
    from_unit = crud_core.get_unit_by_id(db=db, unit_id=from_unit_id)
    to_unit = crud_core.get_unit_by_id(db=db, unit_id=to_unit_id)

    if not from_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"From unit with ID {from_unit_id} not found"
        )
    if not to_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"To unit with ID {to_unit_id} not found"
        )

    can_convert = crud_food.can_convert_food_units(
        db=db,
        food_item_id=food_item_id,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id
    )

    return {"can_convert": can_convert}
