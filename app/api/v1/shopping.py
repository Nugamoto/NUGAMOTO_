"""FastAPI router for shopping system with global products."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.enums import PackageType
from app.crud import shopping as crud_shopping
from app.schemas.shopping import (
    ShoppingListCreate,
    ShoppingListRead,
    ShoppingListUpdate,
    ShoppingProductCreate,
    ShoppingProductRead,
    ShoppingProductUpdate,
    ShoppingProductAssignmentCreate,
    ShoppingProductAssignmentRead,
    ShoppingProductAssignmentUpdate,
    ShoppingProductSearchParams,
    ShoppingProductAssignmentSearchParams,
)

# ================================================================== #
# Router Setup                                                       #
# ================================================================== #

# 🏠 Kitchen-scoped router for Shopping Lists
kitchen_router = APIRouter(prefix="/kitchens", tags=["Shopping - Kitchen"])

# 🌍 Global router for Shopping Products
products_router = APIRouter(prefix="/shopping-products", tags=["Shopping Products"])


# ================================================================== #
# KITCHEN-SCOPED: Shopping List Operations                          #
# ================================================================== #

@kitchen_router.post(
    "/{kitchen_id}/shopping-lists",
    response_model=ShoppingListRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shopping list for a kitchen"
)
def create_shopping_list(
    kitchen_id: int,
    list_data: ShoppingListCreate,
        db: Session = Depends(get_db),
) -> ShoppingListRead:
    """Create a new shopping list for a kitchen."""
    # Ensure kitchen_id matches route parameter
    list_data.kitchen_id = kitchen_id

    try:
        db_list = crud_shopping.create_shopping_list(db, list_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ShoppingListRead.model_validate(db_list, from_attributes=True)


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists",
    response_model=list[ShoppingListRead],
    status_code=status.HTTP_200_OK,
    summary="Get all shopping lists for a kitchen"
)
def get_kitchen_shopping_lists(
    kitchen_id: int,
        db: Session = Depends(get_db)
) -> list[ShoppingListRead]:
    """Retrieve all shopping lists for a kitchen."""
    shopping_lists = crud_shopping.get_kitchen_shopping_lists(db, kitchen_id)
    return [
        ShoppingListRead.model_validate(list_item, from_attributes=True)
        for list_item in shopping_lists
    ]


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists/{list_id}",
    response_model=ShoppingListRead,
    status_code=status.HTTP_200_OK,
    summary="Get a specific shopping list"
)
def get_shopping_list(
    kitchen_id: int,
    list_id: int,
        db: Session = Depends(get_db)
) -> ShoppingListRead:
    """Get a specific shopping list."""
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")

    return ShoppingListRead.model_validate(shopping_list, from_attributes=True)


@kitchen_router.put(
    "/{kitchen_id}/shopping-lists/{list_id}",
    response_model=ShoppingListRead,
    status_code=status.HTTP_200_OK,
    summary="Update a shopping list"
)
def update_shopping_list(
    kitchen_id: int,
    list_id: int,
    list_data: ShoppingListUpdate,
    db: Session = Depends(get_db),
) -> ShoppingListRead:
    """Update a shopping list."""
    # Verify list belongs to kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")

    try:
        updated_list = crud_shopping.update_shopping_list(db, list_id, list_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ShoppingListRead.model_validate(updated_list, from_attributes=True)


@kitchen_router.delete(
    "/{kitchen_id}/shopping-lists/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shopping list"
)
def delete_shopping_list(
    kitchen_id: int,
    list_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """Delete a shopping list."""
    # Verify list belongs to kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")

    try:
        crud_shopping.delete_shopping_list(db, list_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# KITCHEN-SCOPED: Product Assignment Operations                     #
# ================================================================== #

@kitchen_router.post(
    "/{kitchen_id}/shopping-lists/{list_id}/products",
    response_model=ShoppingProductAssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a product to a shopping list"
)
def assign_product_to_list(
    kitchen_id: int,
    list_id: int,
        assignment_data: ShoppingProductAssignmentCreate,
        db: Session = Depends(get_db),
) -> ShoppingProductAssignmentRead:
    """Assign a shopping product to a shopping list."""
    # Verify list belongs to kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")

    try:
        assignment = crud_shopping.assign_product_to_list(db, list_id, assignment_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ShoppingProductAssignmentRead.model_validate(assignment, from_attributes=True)


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists/{list_id}/products",
    response_model=list[ShoppingProductAssignmentRead],
    status_code=status.HTTP_200_OK,
    summary="Get all products assigned to a shopping list"
)
def get_shopping_list_products(
    kitchen_id: int,
    list_id: int,
    is_auto_added: bool | None = Query(None),
    added_by_user_id: int | None = Query(None, gt=0),
    food_item_id: int | None = Query(None, gt=0),
        package_type: PackageType | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[ShoppingProductAssignmentRead]:
    """Get all products assigned to a shopping list with optional filtering."""
    # Verify list belongs to kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")

    search_params = ShoppingProductAssignmentSearchParams(
        is_auto_added=is_auto_added,
        added_by_user_id=added_by_user_id,
        food_item_id=food_item_id,
        package_type=package_type,
    )

    assignments = crud_shopping.get_shopping_list_product_assignments(
        db, list_id, search_params, skip, limit
    )
    return [
        ShoppingProductAssignmentRead.model_validate(assignment, from_attributes=True)
        for assignment in assignments
    ]


@kitchen_router.put(
    "/{kitchen_id}/shopping-lists/{list_id}/products/{product_id}",
    response_model=ShoppingProductAssignmentRead,
    status_code=status.HTTP_200_OK,
    summary="Update a product assignment"
)
def update_product_assignment(
        kitchen_id: int,
        list_id: int,
        product_id: int,
        assignment_data: ShoppingProductAssignmentUpdate,
    db: Session = Depends(get_db),
) -> ShoppingProductAssignmentRead:
    """Update a product assignment."""
    # Verify list belongs to kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")

    try:
        assignment = crud_shopping.update_product_assignment(
            db, list_id, product_id, assignment_data
        )
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ShoppingProductAssignmentRead.model_validate(assignment, from_attributes=True)


@kitchen_router.delete(
    "/{kitchen_id}/shopping-lists/{list_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a product from a shopping list"
)
def remove_product_from_list(
        kitchen_id: int,
        list_id: int,
        product_id: int,
    db: Session = Depends(get_db),
) -> Response:
    """Remove a product assignment from a shopping list."""
    # Verify list belongs to kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if not shopping_list or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, "Shopping list not found in this kitchen")

    try:
        crud_shopping.remove_product_from_list(db, list_id, product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# GLOBAL: Shopping Product Operations                               #
# ================================================================== #

@products_router.post(
    "/",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new global shopping product"
)
def create_shopping_product(
        product_data: ShoppingProductCreate,
        db: Session = Depends(get_db)
) -> ShoppingProductRead:
    """Create a new global shopping product."""
    try:
        db_product = crud_shopping.create_shopping_product(db, product_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ShoppingProductRead.model_validate(db_product, from_attributes=True)


@products_router.get(
    "/",
    response_model=list[ShoppingProductRead],
    status_code=status.HTTP_200_OK,
    summary="Search global shopping products"
)
def search_shopping_products(
    food_item_id: int | None = Query(None, gt=0),
        package_type: PackageType | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
        unit: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[ShoppingProductRead]:
    """Search global shopping products with optional filtering."""
    search_params = ShoppingProductSearchParams(
        food_item_id=food_item_id,
        package_type=package_type,
        min_price=min_price,
        max_price=max_price,
        unit=unit,
    )

    products = crud_shopping.get_all_shopping_products(db, search_params, skip, limit)
    return [
        ShoppingProductRead.model_validate(product, from_attributes=True)
        for product in products
    ]


@products_router.get(
    "/{product_id}",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_200_OK,
    summary="Get a shopping product by ID"
)
def get_shopping_product(
        product_id: int,
    db: Session = Depends(get_db)
) -> ShoppingProductRead:
    """Get a shopping product by ID."""
    product = crud_shopping.get_shopping_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(404, "Shopping product not found")

    return ShoppingProductRead.model_validate(product, from_attributes=True)


@products_router.put(
    "/{product_id}",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_200_OK,
    summary="Update a shopping product"
)
def update_shopping_product(
        product_id: int,
        product_data: ShoppingProductUpdate,
        db: Session = Depends(get_db),
) -> ShoppingProductRead:
    """Update a shopping product."""
    try:
        updated_product = crud_shopping.update_shopping_product(
            db, product_id, product_data
        )
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        else:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ShoppingProductRead.model_validate(updated_product, from_attributes=True)


@products_router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shopping product"
)
def delete_shopping_product(
        product_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a shopping product."""
    try:
        crud_shopping.delete_shopping_product(db, product_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Export routers for backwards compatibility                        #
# ================================================================== #

# Main router for backwards compatibility
router = kitchen_router
