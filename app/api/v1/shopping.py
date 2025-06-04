"""FastAPI router exposing shopping list endpoints."""

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

# ------------------------------------------------------------------ #
# Two Router Approach: Kitchen-scoped + Global                      #
# ------------------------------------------------------------------ #

# 🏠 Kitchen-scoped router for ShoppingList operations
kitchen_router = APIRouter(prefix="/kitchens", tags=["Shopping Lists"])

# 📦 Global router for ShoppingListItem operations  
items_router = APIRouter(prefix="/shopping-list-items", tags=["Shopping List Items"])

# 📊 Global router for summary/analytics
summary_router = APIRouter(prefix="/shopping-lists", tags=["Shopping Lists - Analytics"])


# ================================================================== #
# KITCHEN-SCOPED: ShoppingList Operations                           #
# ================================================================== #

@kitchen_router.post(
    "/{kitchen_id}/shopping-lists",
    response_model=ShoppingListRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shopping list for a kitchen",
)
def create_shopping_list(
    kitchen_id: int,
    list_data: ShoppingListCreate,
    db: Session = Depends(get_db)
) -> ShoppingListRead:
    """Create a new shopping list for a specific kitchen."""
    # Validate kitchen_id matches
    if list_data.kitchen_id != kitchen_id:
        raise HTTPException(400, "Kitchen ID mismatch")
        
    db_list = crud_shopping.create_shopping_list(db, list_data)
    return ShoppingListRead.model_validate(db_list, from_attributes=True)


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists",
    response_model=list[ShoppingListRead],
    status_code=status.HTTP_200_OK,
    summary="Get all shopping lists for a kitchen",
)
def get_kitchen_shopping_lists(
    kitchen_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[ShoppingListRead]:
    """Retrieve all shopping lists for a specific kitchen."""
    lists = crud_shopping.get_shopping_lists_by_kitchen(db, kitchen_id, skip, limit)
    return [ShoppingListRead.model_validate(shopping_list, from_attributes=True) for shopping_list in lists]


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists/{list_id}",
    response_model=ShoppingListWithItems,
    status_code=status.HTTP_200_OK,
    summary="Get shopping list with all items",
)
def get_shopping_list_with_items(
    kitchen_id: int,
    list_id: int,
    db: Session = Depends(get_db),
) -> ShoppingListWithItems:
    """Retrieve a shopping list including all its items."""
    shopping_list = crud_shopping.get_shopping_list_with_items(db, list_id)

    if shopping_list is None:
        raise HTTPException(404, f"Shopping list with ID {list_id} not found")
        
    # Validate list belongs to kitchen
    if shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")

    return ShoppingListWithItems.model_validate(shopping_list, from_attributes=True)


@kitchen_router.put(
    "/{kitchen_id}/shopping-lists/{list_id}",
    response_model=ShoppingListRead,
    status_code=status.HTTP_200_OK,
    summary="Update a shopping list",
)
def update_shopping_list(
    kitchen_id: int,
    list_id: int,
    list_data: ShoppingListUpdate,
    db: Session = Depends(get_db),
) -> ShoppingListRead:
    """Update an existing shopping list."""
    # First verify list belongs to kitchen
    existing = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not existing or existing.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")
        
    updated_list = crud_shopping.update_shopping_list(db, list_id, list_data)
    return ShoppingListRead.model_validate(updated_list, from_attributes=True)


@kitchen_router.delete(
    "/{kitchen_id}/shopping-lists/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shopping list",
)
def delete_shopping_list(
    kitchen_id: int,
    list_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a shopping list and all its items."""
    # Verify list belongs to kitchen
    existing = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not existing or existing.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")
        
    success = crud_shopping.delete_shopping_list(db, list_id)
    if not success:
        raise HTTPException(404, "Shopping list not found")


@kitchen_router.post(
    "/{kitchen_id}/shopping-lists/{list_id}/items",
    response_model=ShoppingListItemRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to a shopping list",
)
def add_shopping_list_item(
    kitchen_id: int,
    list_id: int,
    item_data: ShoppingListItemCreate,
    db: Session = Depends(get_db)
) -> ShoppingListItemRead:
    """Add a new item to a shopping list."""
    # Verify list belongs to kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")
        
    try:
        db_item = crud_shopping.create_shopping_list_item(db, list_id, item_data)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    return ShoppingListItemRead.model_validate(db_item, from_attributes=True)


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists/{list_id}/items",
    response_model=list[ShoppingListItemRead],
    status_code=status.HTTP_200_OK,
    summary="Get items from a shopping list",
)
def get_shopping_list_items(
    kitchen_id: int,
    list_id: int,
    is_auto_added: bool | None = Query(None),
    added_by_user_id: int | None = Query(None, gt=0),
    food_item_id: int | None = Query(None, gt=0),
    package_type: str | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[ShoppingListItemRead]:
    """Retrieve items from a shopping list with optional filtering."""
    # Verify list belongs to kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")
        
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


# ================================================================== #
# GLOBAL: ShoppingListItem Operations                               #
# ================================================================== #

@items_router.get(
    "/{item_id}",
    response_model=ShoppingListItemRead,
    status_code=status.HTTP_200_OK,
    summary="Get a shopping list item by ID",
)
def get_shopping_list_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> ShoppingListItemRead:
    """Get a shopping list item by its global ID."""
    item = crud_shopping.get_shopping_list_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(404, f"Shopping list item with ID {item_id} not found")
    return ShoppingListItemRead.model_validate(item, from_attributes=True)


@items_router.put(
    "/{item_id}",
    response_model=ShoppingListItemRead,
    status_code=status.HTTP_200_OK,
    summary="Update a shopping list item",
)
def update_shopping_list_item(
    item_id: int,
    item_data: ShoppingListItemUpdate,
    db: Session = Depends(get_db),
) -> ShoppingListItemRead:
    """Update an existing shopping list item globally."""
    updated_item = crud_shopping.update_shopping_list_item(db, item_id, item_data)
    if updated_item is None:
        raise HTTPException(404, f"Shopping list item with ID {item_id} not found")
    return ShoppingListItemRead.model_validate(updated_item, from_attributes=True)


@items_router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shopping list item",
)
def delete_shopping_list_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a shopping list item globally."""
    success = crud_shopping.delete_shopping_list_item(db, item_id)
    if not success:
        raise HTTPException(404, f"Shopping list item with ID {item_id} not found")


@items_router.get(
    "/",
    response_model=list[ShoppingListItemRead],
    status_code=status.HTTP_200_OK,
    summary="Search shopping list items globally",
)
def search_shopping_list_items(
    shopping_list_id: int | None = Query(None, gt=0),
    is_auto_added: bool | None = Query(None),
    added_by_user_id: int | None = Query(None, gt=0),
    food_item_id: int | None = Query(None, gt=0),
    package_type: str | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[ShoppingListItemRead]:
    """Search shopping list items globally across all lists."""
    if shopping_list_id:
        # If specific list, use existing function
        search_params = ShoppingListItemSearchParams(
            is_auto_added=is_auto_added,
            added_by_user_id=added_by_user_id,
            food_item_id=food_item_id,
            package_type=package_type,
            min_price=min_price,
            max_price=max_price,
        )
        items = crud_shopping.get_shopping_list_items(db, shopping_list_id, search_params, skip, limit)
    else:
        # Global search across all items (would need new CRUD function)
        # For now, return empty list - implement as needed
        items = []
    
    return [ShoppingListItemRead.model_validate(item, from_attributes=True) for item in items]


# ================================================================== #
# ANALYTICS: Summary Operations                                      #
# ================================================================== #

@summary_router.get(
    "/summary",
    response_model=ShoppingListSummary,
    status_code=status.HTTP_200_OK,
    summary="Get shopping list statistics summary",
)
def get_shopping_summary(
    kitchen_id: int | None = Query(None, gt=0),
    db: Session = Depends(get_db)
) -> ShoppingListSummary:
    """Retrieve summary statistics for shopping lists."""
    return crud_shopping.get_shopping_summary(db, kitchen_id)


# ================================================================== #
# Export all routers                                                #
# ================================================================== #

# Main router for backwards compatibility and easy import
router = kitchen_router