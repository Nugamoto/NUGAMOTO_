"""FastAPI router exposing the shopping endpoints v2.0."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import shopping as crud_shopping
from app.schemas.shopping import (
    ShoppingListCreate, ShoppingListRead, ShoppingListUpdate,
    ShoppingProductCreate, ShoppingProductRead, ShoppingProductUpdate,
    ShoppingProductAssignmentCreate, ShoppingProductAssignmentRead,
    ShoppingProductSearchParams, ShoppingProductAssignmentSearchParams,
    ShoppingListWithProducts
)

# Create sub-routers for better organization
kitchen_router = APIRouter(prefix="/kitchens", tags=["Shopping Lists"])
products_router = APIRouter(prefix="/shopping-products", tags=["Shopping Products"])

# ================================================================== #
# Shopping Product Endpoints (Global Catalog)                       #
# ================================================================== #

@products_router.post(
    "/",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shopping product",
)
def create_shopping_product(
        product_data: ShoppingProductCreate,
        db: Session = Depends(get_db),
) -> ShoppingProductRead:
    """Create a new global shopping product.

    Shopping products define purchasable packages that can be assigned to lists.
    Each product specifies the package size, unit, and equivalent base unit quantity.

    Args:
        product_data: Product data including package details and units.
        db: Injected database session.

    Returns:
        The newly created shopping product.

    Example:
        ```json
        {
            "food_item_id": 1,
            "package_unit_id": 2,
            "package_quantity": 1.0,
            "quantity_in_base_unit": 500.0,
            "package_type": "500 g pack",
            "estimated_price": 2.99
        }
        ```

    Note:
        - package_unit_id: Reference to units table (e.g., "pack", "bottle")
        - quantity_in_base_unit: Equivalent amount in food item's base unit
        - This allows for proper inventory calculations and comparisons
        - If quantity_in_base_unit is not provided, it will be calculated automatically
    """
    try:
        # If quantity_in_base_unit is not provided, calculate it dynamically
        if product_data.quantity_in_base_unit is None:
            try:
                calculated_quantity = crud_shopping.calculate_quantity_in_base_unit(
                    db=db,
                    food_item_id=product_data.food_item_id,
                    package_unit_id=product_data.package_unit_id,
                    package_quantity=product_data.package_quantity
                )
                # Create new product data with calculated quantity
                from app.schemas.shopping import ShoppingProductCreate
                product_data = ShoppingProductCreate(
                    food_item_id=product_data.food_item_id,
                    package_unit_id=product_data.package_unit_id,
                    package_quantity=product_data.package_quantity,
                    quantity_in_base_unit=calculated_quantity,
                    package_type=product_data.package_type,
                    estimated_price=product_data.estimated_price
                )
            except ValueError as conversion_error:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unit conversion failed: {str(conversion_error)}"
                )
        
        db_product = crud_shopping.create_shopping_product(db, product_data)
        return ShoppingProductRead.model_validate(db_product, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@products_router.get(
    "/",
    response_model=list[ShoppingProductRead],
    status_code=status.HTTP_200_OK,
    summary="Search shopping products",
)
def search_shopping_products(
        food_item_id: int | None = Query(None, gt=0, description="Filter by food item"),
        package_unit_id: int | None = Query(None, gt=0, description="Filter by package unit"),
        min_price: float | None = Query(None, ge=0, description="Minimum price filter"),
        max_price: float | None = Query(None, ge=0, description="Maximum price filter"),
        package_type: str | None = Query(None, description="Filter by package type"),
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
        db: Session = Depends(get_db),
) -> list[ShoppingProductRead]:
    """Search and filter shopping products.

    Returns global shopping products that can be assigned to any shopping list.
    Supports filtering by food item, package details, and price range.
    """
    search_params = ShoppingProductSearchParams(
        food_item_id=food_item_id,
        package_unit_id=package_unit_id,
        min_price=min_price,
        max_price=max_price,
        package_type=package_type
    )

    products = crud_shopping.get_all_shopping_products(
        db, search_params, skip, limit
    )
    return [
        ShoppingProductRead.model_validate(product, from_attributes=True)
        for product in products
    ]


@products_router.get(
    "/{product_id}",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_200_OK,
    summary="Get a shopping product by ID",
)
def get_shopping_product(
        product_id: int,
        db: Session = Depends(get_db),
) -> ShoppingProductRead:
    """Get a specific shopping product by its ID."""
    product = crud_shopping.get_shopping_product_by_id(db, product_id)
    if product is None:
        raise HTTPException(404, f"Shopping product with ID {product_id} not found")
    return ShoppingProductRead.model_validate(product, from_attributes=True)


@products_router.patch(
    "/{product_id}",
    response_model=ShoppingProductRead,
    status_code=status.HTTP_200_OK,
    summary="Update a shopping product",
)
def update_shopping_product(
        product_id: int,
        product_data: ShoppingProductUpdate,
        db: Session = Depends(get_db),
) -> ShoppingProductRead:
    """Update an existing shopping product.

    Note: Changes to package quantities or units will affect all existing
    assignments of this product to shopping lists.
    """
    try:
        updated_product = crud_shopping.update_shopping_product(
            db, product_id, product_data
        )
        if updated_product is None:
            raise HTTPException(404, f"Shopping product with ID {product_id} not found")
        return ShoppingProductRead.model_validate(updated_product, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@products_router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shopping product",
)
def delete_shopping_product(
        product_id: int,
        db: Session = Depends(get_db),
) -> None:
    """Delete a shopping product.

    This will fail if the product is assigned to any shopping lists.
    """
    success = crud_shopping.delete_shopping_product(db, product_id)
    if not success:
        raise HTTPException(404, f"Shopping product with ID {product_id} not found")


@products_router.get(
    "/food-item/{food_item_id}",
    response_model=list[ShoppingProductRead],
    status_code=status.HTTP_200_OK,
    summary="Get all products for a food item",
)
def get_products_for_food_item(
        food_item_id: int,
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
        db: Session = Depends(get_db),
) -> list[ShoppingProductRead]:
    """Get all available shopping products for a specific food item.

    Useful for showing different package options when adding items to shopping lists.
    """
    products = crud_shopping.get_products_for_food_item(
        db, food_item_id, skip, limit
    )
    return [
        ShoppingProductRead.model_validate(product, from_attributes=True)
        for product in products
    ]


# ================================================================== #
# Shopping List Management                                           #
# ================================================================== #

@kitchen_router.post(
    "/{kitchen_id}/shopping-lists/",
    response_model=ShoppingListRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shopping list",
)
def create_shopping_list(
        kitchen_id: int,
        list_data: ShoppingListCreate,
        db: Session = Depends(get_db),
) -> ShoppingListRead:
    """Create a new shopping list for a kitchen.

    Args:
        kitchen_id: The ID of the kitchen.
        list_data: Shopping list data.
        db: Injected database session.

    Returns:
        The newly created shopping list.

    Example:
        ```json
        {
            "name": "Weekly Shopping",
            "type": "SUPERMARKET"
        }
        ```
    """
    # Ensure kitchen_id matches the data
    list_data.kitchen_id = kitchen_id

    db_list = crud_shopping.create_shopping_list(db, list_data)
    return ShoppingListRead.model_validate(db_list, from_attributes=True)


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists/",
    response_model=list[ShoppingListRead],
    status_code=status.HTTP_200_OK,
    summary="Get all shopping lists for a kitchen",
)
def get_kitchen_shopping_lists(
        kitchen_id: int,
        db: Session = Depends(get_db),
) -> list[ShoppingListRead]:
    """Get all shopping lists for a specific kitchen."""
    lists = crud_shopping.get_kitchen_shopping_lists(db, kitchen_id)
    return [
        ShoppingListRead.model_validate(shopping_list, from_attributes=True)
        for shopping_list in lists
    ]


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists/{list_id}",
    response_model=ShoppingListWithProducts,
    status_code=status.HTTP_200_OK,
    summary="Get a shopping list with products",
)
def get_shopping_list(
        kitchen_id: int,
        list_id: int,
        db: Session = Depends(get_db),
) -> ShoppingListWithProducts:
    """Get a shopping list with all assigned products and calculated totals."""
    shopping_list = crud_shopping.get_shopping_list_with_products(db, list_id)
    if shopping_list is None:
        raise HTTPException(404, f"Shopping list with ID {list_id} not found")

    # Verify the list belongs to the specified kitchen
    if shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, f"Shopping list {list_id} not found in kitchen {kitchen_id}")

    return shopping_list


@kitchen_router.patch(
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
    updated_list = crud_shopping.update_shopping_list(db, list_id, list_data)
    if updated_list is None:
        raise HTTPException(404, f"Shopping list with ID {list_id} not found")

    # Verify the list belongs to the specified kitchen
    if updated_list.kitchen_id != kitchen_id:
        raise HTTPException(404, f"Shopping list {list_id} not found in kitchen {kitchen_id}")
    
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
    """Delete a shopping list and all its product assignments."""
    # First verify the list exists and belongs to the kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if shopping_list is None or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, f"Shopping list {list_id} not found in kitchen {kitchen_id}")

    success = crud_shopping.delete_shopping_list(db, list_id)
    if not success:
        raise HTTPException(404, f"Shopping list with ID {list_id} not found")


# ================================================================== #
# Product Assignment Endpoints                                       #
# ================================================================== #

@kitchen_router.post(
    "/{kitchen_id}/shopping-lists/{list_id}/products",
    response_model=ShoppingProductAssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a product to a shopping list",
)
def assign_product_to_list(
        kitchen_id: int,
        list_id: int,
        assignment_data: ShoppingProductAssignmentCreate,
        db: Session = Depends(get_db),
) -> ShoppingProductAssignmentRead:
    """Assign an existing shopping product to a shopping list.

    Args:
        kitchen_id: The ID of the kitchen.
        list_id: The ID of the shopping list.
        assignment_data: Assignment data including product ID and optional note.
        db: Injected database session.

    Returns:
        The created assignment with full product details.

    Example:
        ```json
        {
            "shopping_product_id": 1,
            "added_by_user_id": 123,
            "is_auto_added": false,
            "note": "Need this for dinner tonight"
        }
        ```

    Note:
        - The same product cannot be assigned to the same list twice
        - Use update endpoint to modify existing assignments
    """
    try:
        # Verify the list belongs to the kitchen
        shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
        if shopping_list is None or shopping_list.kitchen_id != kitchen_id:
            raise HTTPException(404, f"Shopping list {list_id} not found in kitchen {kitchen_id}")

        db_assignment = crud_shopping.assign_product_to_list(
            db, list_id, assignment_data
        )
        return ShoppingProductAssignmentRead.model_validate(
            db_assignment, from_attributes=True
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@kitchen_router.get(
    "/{kitchen_id}/shopping-lists/{list_id}/products",
    response_model=list[ShoppingProductAssignmentRead],
    status_code=status.HTTP_200_OK,
    summary="Get all products on a shopping list",
)
def get_shopping_list_products(
        kitchen_id: int,
        list_id: int,
        is_auto_added: bool | None = Query(None, description="Filter by auto-added status"),
        added_by_user_id: int | None = Query(None, gt=0, description="Filter by user who added"),
        food_item_id: int | None = Query(None, gt=0, description="Filter by food item"),
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
        db: Session = Depends(get_db),
) -> list[ShoppingProductAssignmentRead]:
    """Get all products assigned to a shopping list with optional filtering.

    Returns detailed information about each product including package details,
    estimated prices, and assignment metadata.
    """
    # Verify the list belongs to the kitchen
    shopping_list = crud_shopping.get_shopping_list_by_id(db, list_id)
    if shopping_list is None or shopping_list.kitchen_id != kitchen_id:
        raise HTTPException(404, f"Shopping list {list_id} not found in kitchen {kitchen_id}")
    
    search_params = ShoppingProductAssignmentSearchParams(
        is_auto_added=is_auto_added,
        added_by_user_id=added_by_user_id,
        food_item_id=food_item_id
    )

    assignments = crud_shopping.get_shopping_list_product_assignments(
        db, list_id, search_params, skip, limit
    )
    return [
        ShoppingProductAssignmentRead.model_validate(assignment, from_attributes=True)
        for assignment in assignments
    ]
