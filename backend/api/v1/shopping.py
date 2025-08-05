"""FastAPI router exposing the shopping management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.crud import shopping as crud_shopping
from backend.schemas.shopping import (
    ShoppingListCreate, ShoppingListRead, ShoppingListUpdate,
    ShoppingProductCreate, ShoppingProductRead, ShoppingProductUpdate,
    ShoppingProductAssignmentCreate, ShoppingProductAssignmentRead, ShoppingProductAssignmentUpdate,
    ShoppingProductSearchParams, ShoppingProductAssignmentSearchParams,
    ShoppingListWithProducts, ShoppingProductCreateWithAssignment
)

# ================================================================== #
# Sub-routers for better organization                               #
# ================================================================== #

lists_router = APIRouter(prefix="/kitchens/{kitchen_id}/shopping-lists", tags=["Shopping Lists"])
assignments_router = APIRouter(prefix="/kitchens/{kitchen_id}/shopping-lists/{list_id}/products", tags=["Shopping List Product Assignments"])
products_router = APIRouter(prefix="/shopping-products", tags=["Shopping Products"])


# ================================================================== #
# Shopping Products Management (Global)                             #
# ================================================================== #

@products_router.post(
    "/",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create shopping product"
)
def create_shopping_product(
    product_data: ShoppingProductCreate,
    db: Session = Depends(get_db)
) -> ShoppingProductRead:
    """Create a new global shopping product.

    Creates a reusable product that can be assigned to multiple shopping lists.
    Each product represents a specific package type (e.g., "500g pack", "1L bottle").

    Args:
        product_data: Shopping product data to create.
        db: Database session dependency.

    Returns:
        The created shopping product with computed fields.

    Raises:
        HTTPException:
            * 404 – if food item or package unit not found.
            * 400 – for validation errors.

    Example:
        ```json
        {
            "food_item_id": 1,
            "package_unit_id": 2,
            "package_quantity": 500.0,
            "quantity_in_base_unit": 500.0,
            "package_type": "500 g pack",
            "estimated_price": 2.99
        }
        ```
    """
    try:
        return crud_shopping.create_shopping_product(db, product_data)
    except ValueError as exc:
        error_msg = str(exc)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        ) from exc


@products_router.get(
    "/",
    response_model=list[ShoppingProductRead],
    status_code=status.HTTP_200_OK,
    summary="Search shopping products"
)
def search_shopping_products(
    food_item_id: int | None = Query(None, description="Filter by food item ID"),
    package_unit_id: int | None = Query(None, description="Filter by package unit ID"),
    min_price: float | None = Query(None, description="Minimum price filter"),
    max_price: float | None = Query(None, description="Maximum price filter"),
    package_type: str | None = Query(None, description="Package type contains filter"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    db: Session = Depends(get_db)
) -> list[ShoppingProductRead]:
    """Search shopping products with filters.

    Supports filtering by food item, package unit, price range, and package type.
    Results are ordered by creation date (newest first).

    Args:
        food_item_id: Optional food item ID filter.
        package_unit_id: Optional package unit ID filter.
        min_price: Optional minimum price filter.
        max_price: Optional maximum price filter.
        package_type: Optional package type contains filter.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.
        db: Database session dependency.

    Returns:
        List of shopping products matching the filters.
    """
    search_params = ShoppingProductSearchParams(
        food_item_id=food_item_id,
        package_unit_id=package_unit_id,
        min_price=min_price,
        max_price=max_price,
        package_type=package_type
    )

    return crud_shopping.get_all_shopping_products(
        db, search_params=search_params, skip=skip, limit=limit
    )


@products_router.get(
    "/{product_id}",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_200_OK,
    summary="Get shopping product by ID"
)
def get_shopping_product(
    product_id: int,
    db: Session = Depends(get_db)
) -> ShoppingProductRead:
    """Get a shopping product by ID.

    Args:
        product_id: Primary key of the shopping product.
        db: Database session dependency.

    Returns:
        The requested shopping product with computed fields.

    Raises:
        HTTPException: 404 if the shopping product does not exist.
    """
    product = crud_shopping.get_shopping_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping product not found"
        )
    return product


@products_router.patch(
    "/{product_id}",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_200_OK,
    summary="Update shopping product"
)
def update_shopping_product(
    product_id: int,
    product_data: ShoppingProductUpdate,
    db: Session = Depends(get_db)
) -> ShoppingProductRead:
    """Update an existing shopping product.

    Args:
        product_id: Primary key of the shopping product.
        product_data: Partial shopping product data for updates.
        db: Database session dependency.

    Returns:
        The updated shopping product.

    Raises:
        HTTPException: 404 if the shopping product does not exist.
    """
    product = crud_shopping.update_shopping_product(db, product_id, product_data)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping product not found"
        )
    return product


@products_router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete shopping product"
)
def delete_shopping_product(
    product_id: int,
    db: Session = Depends(get_db)
) -> Response:
    """Delete a shopping product.

    Args:
        product_id: Primary key of the shopping product.
        db: Database session dependency.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException:
            * 404 – if the shopping product does not exist.
            * 400 – if the product is assigned to shopping lists.
    """
    try:
        deleted = crud_shopping.delete_shopping_product(db, product_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shopping product not found"
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc


@products_router.get(
    "/by-food-item/{food_item_id}",
    response_model=list[ShoppingProductRead],
    status_code=status.HTTP_200_OK,
    summary="Get products for food item"
)
def get_products_for_food_item(
    food_item_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    db: Session = Depends(get_db)
) -> list[ShoppingProductRead]:
    """Get all shopping products for a specific food item.

    Useful for finding different package options for the same food item.
    Results are ordered by package quantity.

    Args:
        food_item_id: Primary key of the food item.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.
        db: Database session dependency.

    Returns:
        List of shopping products for the food item.
    """
    return crud_shopping.get_products_for_food_item(
        db, food_item_id, skip=skip, limit=limit
    )


# ================================================================== #
# Shopping Lists Management (Kitchen-scoped)                        #
# ================================================================== #

@lists_router.post(
    "/",
    response_model=ShoppingListRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create shopping list"
)
def create_shopping_list(
    kitchen_id: int,
    list_data: ShoppingListCreate,
    db: Session = Depends(get_db)
) -> ShoppingListRead:
    """Create a new shopping list for a kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        list_data: Shopping list data to create.
        db: Database session dependency.

    Returns:
        The created shopping list.

    Raises:
        HTTPException: 404 if kitchen not found.

    Example:
        ```json
        {
            "name": "Weekly Shopping",
            "type": "supermarket"
        }
        ```
    """
    # Ensure kitchen_id matches the path parameter
    list_data.kitchen_id = kitchen_id

    try:
        return crud_shopping.create_shopping_list(db, list_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        ) from exc


@lists_router.get(
    "/",
    response_model=list[ShoppingListRead],
    status_code=status.HTTP_200_OK,
    summary="Get kitchen shopping lists"
)
def get_kitchen_shopping_lists(
    kitchen_id: int,
    db: Session = Depends(get_db)
) -> list[ShoppingListRead]:
    """Get all shopping lists for a kitchen.

    Args:
        kitchen_id: Primary key of the kitchen.
        db: Database session dependency.

    Returns:
        List of shopping lists ordered by creation date (newest first).
    """
    return crud_shopping.get_kitchen_shopping_lists(db, kitchen_id)


@lists_router.get(
    "/{list_id}",
    response_model=ShoppingListRead,
    status_code=status.HTTP_200_OK,
    summary="Get shopping list by ID"
)
def get_shopping_list(
    kitchen_id: int,
    list_id: int,
    db: Session = Depends(get_db)
) -> ShoppingListRead:
    """Get a shopping list by ID.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        db: Database session dependency.

    Returns:
        The requested shopping list.

    Raises:
        HTTPException: 404 if the shopping list does not exist or doesn't belong to kitchen.
    """
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    # Verify list belongs to the specified kitchen
    if shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    return shopping_list


@lists_router.get(
    "/{list_id}/with-products",
    response_model=ShoppingListWithProducts,
    status_code=status.HTTP_200_OK,
    summary="Get shopping list with products and totals"
)
def get_shopping_list_with_products(
    kitchen_id: int,
    list_id: int,
    db: Session = Depends(get_db)
) -> ShoppingListWithProducts:
    """Get a shopping list with all assigned products and calculated totals.

    This endpoint provides a complete view of the shopping list including
    - All assigned products with details
    - Total product count
    - Estimated total price

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        db: Database session dependency.

    Returns:
        The shopping list with products and calculated totals.

    Raises:
        HTTPException: 404 if the shopping list does not exist or doesn't belong to kitchen.
    """
    # First verify the list exists and belongs to the kitchen
    existing_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    if existing_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    # Get the list with products
    list_with_products = crud_shopping.get_shopping_list_with_products(db, list_id)
    if list_with_products is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    return list_with_products


@lists_router.patch(
    "/{list_id}",
    response_model=ShoppingListRead,
    status_code=status.HTTP_200_OK,
    summary="Update shopping list"
)
def update_shopping_list(
    kitchen_id: int,
    list_id: int,
    list_data: ShoppingListUpdate,
    db: Session = Depends(get_db)
) -> ShoppingListRead:
    """Update an existing shopping list.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        list_data: Partial shopping list data for updates.
        db: Database session dependency.

    Returns:
        The updated shopping list.

    Raises:
        HTTPException: 404 if the shopping list does not exist or doesn't belong to kitchen.
    """
    # First verify the list exists and belongs to the kitchen
    existing_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    if existing_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    # Proceed with update
    updated_list = crud_shopping.update_shopping_list(db, list_id, list_data)
    if updated_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    return updated_list


@lists_router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete shopping list"
)
def delete_shopping_list(
    kitchen_id: int,
    list_id: int,
    db: Session = Depends(get_db)
) -> Response:
    """Delete a shopping list.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        db: Database session dependency.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the shopping list does not exist or doesn't belong to kitchen.

    Note:
        This will also delete all product assignments.
    """
    # First verify the list exists and belongs to the kitchen
    existing_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    if existing_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    # Proceed with deletion
    deleted = crud_shopping.delete_shopping_list(db, list_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Shopping List Product Assignments                                 #
# ================================================================== #

@assignments_router.post(
    "/",
    response_model=ShoppingProductAssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign product to shopping list"
)
def assign_product_to_list(
    kitchen_id: int,
    list_id: int,
    assignment_data: ShoppingProductAssignmentCreate,
    db: Session = Depends(get_db)
) -> ShoppingProductAssignmentRead:
    """Assign a shopping product to a shopping list.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        assignment_data: Product assignment data.
        db: Database session dependency.

    Returns:
        The created product assignment.

    Raises:
        HTTPException:
            * 404 – if shopping list or product not found, or list doesn't belong to kitchen.
            * 400 – if product already assigned to this list.

    Example:
        ```json
        {
            "shopping_product_id": 1,
            "added_by_user_id": 123,
            "note": "Need this for dinner tonight"
        }
        ```
    """
    # First verify the list exists and belongs to the kitchen
    existing_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    if existing_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    try:
        return crud_shopping.assign_product_to_list(db, list_id, assignment_data)
    except ValueError as exc:
        error_msg = str(exc)
        if "already assigned" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            ) from exc
        elif "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        ) from exc


@assignments_router.post(
    "/create-and-assign",
    response_model=ShoppingProductAssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create product and assign to shopping list"
)
def create_product_and_assign_to_list(
    kitchen_id: int,
    list_id: int,
    create_data: ShoppingProductCreateWithAssignment,
    db: Session = Depends(get_db)
) -> ShoppingProductAssignmentRead:
    """Create a new shopping product and immediately assign it to a shopping list.

    This is a convenience endpoint that combines product creation and assignment
    into a single atomic operation. Useful when you need a product that doesn't
    exist yet in the global catalog.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        create_data: Combined product and assignment data.
        db: Database session dependency.

    Returns:
        The created product assignment with product details.

    Raises:
        HTTPException:
            * 404 – if shopping list not found or doesn't belong to kitchen.
            * 400 – for validation errors.

    Example:
        ```json
        {
            "food_item_id": 1,
            "package_unit_id": 2,
            "package_quantity": 500.0,
            "quantity_in_base_unit": 500.0,
            "package_type": "500 g pack",
            "estimated_price": 2.99,
            "added_by_user_id": 123,
            "note": "For tonight's dinner"
        }
        ```
    """
    # First verify the list exists and belongs to the kitchen
    existing_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    if existing_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    try:
        # Split the data into product and assignment parts
        from backend.schemas.shopping import ShoppingProductCreate, ShoppingProductAssignmentCreate

        product_data = ShoppingProductCreate(
            food_item_id=create_data.food_item_id,
            package_unit_id=create_data.package_unit_id,
            package_quantity=create_data.package_quantity,
            quantity_in_base_unit=create_data.quantity_in_base_unit,
            package_type=create_data.package_type,
            estimated_price=create_data.estimated_price
        )

        assignment_data = ShoppingProductAssignmentCreate(
            shopping_product_id=0,  # Will be set by the CRUD function
            added_by_user_id=create_data.added_by_user_id,
            is_auto_added=create_data.is_auto_added,
            note=create_data.note
        )

        # Create product and assignment in one transaction
        product_schema, assignment_schema = crud_shopping.create_product_and_assign_to_list(
            db, list_id, product_data, assignment_data
        )

        return assignment_schema

    except ValueError as exc:
        error_msg = str(exc)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        ) from exc


@assignments_router.get(
    "/",
    response_model=list[ShoppingProductAssignmentRead],
    status_code=status.HTTP_200_OK,
    summary="Get shopping list products"
)
def get_shopping_list_products(
    kitchen_id: int,
    list_id: int,
    is_auto_added: bool | None = Query(None, description="Filter by auto-added status"),
    added_by_user_id: int | None = Query(None, description="Filter by user who added"),
    food_item_id: int | None = Query(None, description="Filter by food item ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    db: Session = Depends(get_db)
) -> list[ShoppingProductAssignmentRead]:
    """Get all products assigned to a shopping list.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        is_auto_added: Optional filter for auto-added items.
        added_by_user_id: Optional filter for user who added items.
        food_item_id: Optional filter for specific food item.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.
        db: Database session dependency.

    Returns:
        List of product assignments with shopping product details.

    Raises:
        HTTPException: 404 if shopping list doesn't exist or doesn't belong to kitchen.
    """
    # First verify the list exists and belongs to the kitchen
    existing_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    if existing_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    search_params = ShoppingProductAssignmentSearchParams(
        is_auto_added=is_auto_added,
        added_by_user_id=added_by_user_id,
        food_item_id=food_item_id
    )

    return crud_shopping.get_shopping_list_product_assignments(
        db, list_id, search_params=search_params, skip=skip, limit=limit
    )


@assignments_router.patch(
    "/{product_id}",
    response_model=ShoppingProductAssignmentRead,
    status_code=status.HTTP_200_OK,
    summary="Update product assignment"
)
def update_product_assignment(
    kitchen_id: int,
    list_id: int,
    product_id: int,
    assignment_data: ShoppingProductAssignmentUpdate,
    db: Session = Depends(get_db)
) -> ShoppingProductAssignmentRead:
    """Update a product assignment on a shopping list.

    Allows updating assignment-specific fields like notes.
    Cannot change which product is assigned - use delete or create for that.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        product_id: Primary key of the shopping product.
        assignment_data: Partial assignment data for updates.
        db: Database session dependency.

    Returns:
        The updated product assignment.

    Raises:
        HTTPException: 404 if the shopping list, product, or assignment doesn't exist.

    Example:
        ```json
        {
            "note": "Updated note - get the organic version"
        }
        ```
    """
    # First verify the list exists and belongs to the kitchen
    existing_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    if existing_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    # Update the assignment
    updated_assignment = crud_shopping.update_product_assignment(
        db, list_id, product_id, assignment_data
    )

    if updated_assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product assignment not found"
        )

    return updated_assignment


@assignments_router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove product from shopping list"
)
def remove_product_from_list(
    kitchen_id: int,
    list_id: int,
    product_id: int,
    db: Session = Depends(get_db)
) -> Response:
    """Remove a product assignment from a shopping list.

    This only removes the assignment, not the global shopping product.
    The product can still be assigned to other shopping lists.

    Args:
        kitchen_id: Primary key of the kitchen (for path consistency).
        list_id: Primary key of the shopping list.
        product_id: Primary key of the shopping product.
        db: Database session dependency.

    Returns:
        Response with 204 status code.

    Raises:
        HTTPException: 404 if the shopping list or assignment doesn't exist.
    """
    # First verify the list exists and belongs to the kitchen
    existing_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if existing_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found"
        )

    if existing_list.kitchen_id != kitchen_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shopping list not found in this kitchen"
        )

    # Remove the assignment
    removed = crud_shopping.remove_product_from_list(db, list_id, product_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product assignment not found"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ================================================================== #
# Main Router Assembly                                               #
# ================================================================== #

router = APIRouter(prefix="/shopping")

# Include all sub-routers
router.include_router(lists_router)
router.include_router(assignments_router)
router.include_router(products_router)