"""FastAPI router exposing the /shopping-lists endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import shopping as crud_shopping
from app.schemas.shopping import (
    ShoppingListCreate,
    ShoppingListRead,
    ShoppingListUpdate,
    ShoppingListWithItems,
    ShoppingListItemCreate,
    ShoppingListItemRead,
    ShoppingListItemUpdate,
    ShoppingListItemSearchParams,
    ShoppingListSummary
)

router = APIRouter(prefix="/shopping-lists", tags=["Shopping Lists"])


# ------------------------------------------------------------------ #
# Shopping List Routes                                               #
# ------------------------------------------------------------------ #

@router.post(
    "/",
    response_model=ShoppingListRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shopping list",
)
def create_shopping_list(
        list_data: ShoppingListCreate,
        db: Session = Depends(get_db)
) -> ShoppingListRead:
    """Create a new shopping list for a kitchen.

    This endpoint allows users to create shopping lists categorized by type
    (supermarket, online, farmers market, etc.). Each list belongs to a specific kitchen.

    Args:
        list_data: Validated shopping list payload.
        db: Injected database session.

    Returns:
        The newly created shopping list with timestamp and ID.

    Example:
        ```json
        {
            "kitchen_id": 123,
            "name": "Edeka Wocheneinkauf",
            "type": "supermarket"
        }
        ```

    Note:
        This endpoint is used by kitchen members to organize their shopping
        by different stores or shopping methods.
    """
    db_list = crud_shopping.create_shopping_list(db, list_data)
    return ShoppingListRead.model_validate(db_list, from_attributes=True)


@router.get(
    "/kitchens/{kitchen_id}/shopping-lists/",
    response_model=list[ShoppingListRead],
    status_code=status.HTTP_200_OK,
    summary="Get all shopping lists for a kitchen",
)
def get_kitchen_shopping_lists(
        kitchen_id: int,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
        db: Session = Depends(get_db),
) -> list[ShoppingListRead]:
    """Retrieve all shopping lists for a specific kitchen.

    Returns shopping lists ordered by creation time (newest first) with pagination support.

    Args:
        kitchen_id: The kitchen ID to filter by.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.
        db: Injected database session.

    Returns:
        A list of shopping lists for the kitchen.

    Example:
        ```
        GET /shopping-lists/kitchens/123/shopping-lists/?skip=0&limit=10
        ```

    Note:
        This endpoint helps users see all their shopping lists organized
        by different stores and shopping methods.
    """
    lists = crud_shopping.get_shopping_lists_by_kitchen(db, kitchen_id, skip, limit)
    return [ShoppingListRead.model_validate(shopping_list, from_attributes=True) for shopping_list in lists]


@router.get(
    "/{list_id}",
    response_model=ShoppingListWithItems,
    status_code=status.HTTP_200_OK,
    summary="Get shopping list with all items",
)
def get_shopping_list_with_items(
        list_id: int,
        db: Session = Depends(get_db),
) -> ShoppingListWithItems:
    """Retrieve a shopping list including all its items.

    Args:
        list_id: The unique identifier of the shopping list.
        db: Injected database session.

    Returns:
        The shopping list with all associated items.

    Raises:
        HTTPException: 404 if the shopping list is not found.

    Example:
        ```
        GET /shopping-lists/123
        ```

    Note:
        This endpoint provides a complete view of a shopping list
        including all items with quantities, units, and pricing information.
    """
    shopping_list = crud_shopping.get_shopping_list_with_items(db, list_id)

    if shopping_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list with ID {list_id} not found"
        )

    return ShoppingListWithItems.model_validate(shopping_list, from_attributes=True)


@router.put(
    "/{list_id}",
    response_model=ShoppingListRead,
    status_code=status.HTTP_200_OK,
    summary="Update a shopping list",
)
def update_shopping_list(
        list_id: int,
        list_data: ShoppingListUpdate,
        db: Session = Depends(get_db),
) -> ShoppingListRead:
    """Update an existing shopping list.

    Args:
        list_id: The unique identifier of the shopping list.
        list_data: Validated update payload.
        db: Injected database session.

    Returns:
        The updated shopping list.

    Raises:
        HTTPException: 404 if the shopping list is not found.

    Example:
        ```json
        {
            "name": "Updated List Name",
            "type": "online"
        }
        ```

    Note:
        This endpoint allows users to rename lists or change their type
        (e.g., from supermarket to online shopping).
    """
    updated_list = crud_shopping.update_shopping_list(db, list_id, list_data)

    if updated_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list with ID {list_id} not found"
        )

    return ShoppingListRead.model_validate(updated_list, from_attributes=True)


@router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shopping list",
)
def delete_shopping_list(
        list_id: int,
        db: Session = Depends(get_db),
) -> None:
    """Delete a shopping list and all its items.

    Args:
        list_id: The unique identifier of the shopping list to delete.
        db: Injected database session.

    Raises:
        HTTPException: 404 if the shopping list is not found.

    Example:
        ```
        DELETE /shopping-lists/123
        ```

    Note:
        This operation is irreversible and will delete all items in the list.
        Use with caution.
    """
    success = crud_shopping.delete_shopping_list(db, list_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list with ID {list_id} not found"
        )


# ------------------------------------------------------------------ #
# Shopping List Item Routes                                          #
# ------------------------------------------------------------------ #

@router.post(
    "/{list_id}/items/",
    response_model=ShoppingListItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to a shopping list",
)
def add_shopping_list_item(
        list_id: int,
        item_data: ShoppingListItemCreate,
        db: Session = Depends(get_db)
) -> ShoppingListItemRead:
    """Add a new item to a shopping list.

    Items can be added manually by users or automatically by the AI system.
    Each item includes quantity, unit, optional packaging type and estimated price.

    Args:
        list_id: The shopping list ID.
        item_data: Validated shopping list item payload.
        db: Injected database session.

    Returns:
        The newly created shopping list item.

    Raises:
        HTTPException: 404 if the shopping list is not found.

    Example:
        ```json
        {
            "food_item_id": 456,
            "quantity": 2.5,
            "unit": "kg",
            "package_type": "lose",
            "estimated_price": 3.50,
            "is_auto_added": false,
            "added_by_user_id": 789
        }
        ```

    Note:
        This endpoint supports both manual additions by users and
        automatic additions by AI services based on recipes and inventory.
    """
    try:
        db_item = crud_shopping.create_shopping_list_item(db, list_id, item_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        ) from exc

    return ShoppingListItemRead.model_validate(db_item, from_attributes=True)


@router.get(
    "/{list_id}/items/",
    response_model=list[ShoppingListItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get items from a shopping list with optional filtering",
)
def get_shopping_list_items(
        list_id: int,
        is_auto_added: bool | None = Query(None, description="Filter by auto-added status"),
        added_by_user_id: int | None = Query(None, gt=0, description="Filter by user who added"),
        food_item_id: int | None = Query(None, gt=0, description="Filter by food item"),
        package_type: str | None = Query(None, description="Filter by package type"),
        min_price: float | None = Query(None, ge=0, description="Minimum estimated price"),
        max_price: float | None = Query(None, ge=0, description="Maximum estimated price"),
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
        db: Session = Depends(get_db),
) -> list[ShoppingListItemRead]:
    """Retrieve items from a shopping list with optional filtering.

    Supports various filters to help users find specific items or analyze
    shopping patterns (auto vs manual additions, price ranges, etc.).

    Args:
        list_id: The shopping list ID.
        is_auto_added: Optional filter for auto-added vs manual items.
        added_by_user_id: Optional filter for items added by specific user.
        food_item_id: Optional filter for specific food item.
        package_type: Optional filter for package type.
        min_price: Optional minimum price filter.
        max_price: Optional maximum price filter.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.
        db: Injected database session.

    Returns:
        A list of shopping list items matching the criteria.

    Example:
        ```
        GET /shopping-lists/123/items/?is_auto_added=false&min_price=2.0&limit=20
        ```

    Note:
        This endpoint enables detailed analysis of shopping lists and
        helps users understand AI vs manual shopping recommendations.
    """
    search_params = ShoppingListItemSearchParams(
        is_auto_added=is_auto_added,
        added_by_user_id=added_by_user_id,
        food_item_id=food_item_id,
        package_type=package_type,
        min_price=min_price,
        max_price=max_price,
    )

    items = crud_shopping.get_shopping_list_items(db, list_id, search_params, skip, limit)
    return [ShoppingListItemRead.model_validate(item, from_attributes=True) for item in items]


@router.put(
    "/items/{item_id}",
    response_model=ShoppingListItemRead,
    status_code=status.HTTP_200_OK,
    summary="Update a shopping list item",
)
def update_shopping_list_item(
        item_id: int,
        item_data: ShoppingListItemUpdate,
        db: Session = Depends(get_db),
) -> ShoppingListItemRead:
    """Update an existing shopping list item.

    Allows updating quantity, unit, package type, estimated price,
    and auto-added status. Useful for adjusting quantities or correcting information.

    Args:
        item_id: The unique identifier of the shopping list item.
        item_data: Validated update payload.
        db: Injected database session.

    Returns:
        The updated shopping list item.

    Raises:
        HTTPException: 404 if the shopping list item is not found.

    Example:
        ```json
        {
            "quantity": 5.0,
            "estimated_price": 7.25,
            "package_type": "dose"
        }
        ```

    Note:
        This endpoint enables users to adjust shopping lists based on
        actual store availability, price changes, or quantity needs.
    """
    updated_item = crud_shopping.update_shopping_list_item(db, item_id, item_data)

    if updated_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item with ID {item_id} not found"
        )

    return ShoppingListItemRead.model_validate(updated_item, from_attributes=True)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shopping list item",
)
def delete_shopping_list_item(
        item_id: int,
        db: Session = Depends(get_db),
) -> None:
    """Delete a shopping list item.

    Args:
        item_id: The unique identifier of the shopping list item to delete.
        db: Injected database session.

    Raises:
        HTTPException: 404 if the shopping list item is not found.

    Example:
        ```
        DELETE /shopping-lists/items/456
        ```

    Note:
        This operation removes individual items from shopping lists.
        Useful when items are no longer needed or were added by mistake.
    """
    success = crud_shopping.delete_shopping_list_item(db, item_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item with ID {item_id} not found"
        )


# ------------------------------------------------------------------ #
# Summary and Analytics Routes                                       #
# ------------------------------------------------------------------ #

@router.get(
    "/summary",
    response_model=ShoppingListSummary,
    status_code=status.HTTP_200_OK,
    summary="Get shopping list statistics summary",
)
def get_shopping_summary(
        kitchen_id: int | None = Query(None, gt=0, description="Optional kitchen filter"),
        db: Session = Depends(get_db)
) -> ShoppingListSummary:
    """Retrieve summary statistics for shopping lists.

    Provides overview statistics including total counts, breakdowns by type,
    auto vs manual additions, and total estimated value.

    Args:
        kitchen_id: Optional filter for specific kitchen.
        db: Injected database session.

    Returns:
        Summary statistics for shopping lists and items.

    Example Response:
        ```json
        {
            "total_lists": 15,
            "total_items": 120,
            "items_by_type": {
                "supermarket": 8,
                "online": 5,
                "farmers_market": 2
            },
            "auto_added_items": 75,
            "manual_items": 45,
            "total_estimated_value": 245.50
        }
        ```

    Note:
        This endpoint provides valuable insights for kitchen management
        and understanding AI vs manual shopping patterns.
    """
    return crud_shopping.get_shopping_summary(db, kitchen_id)
