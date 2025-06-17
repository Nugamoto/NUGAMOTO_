"""CRUD operations for shopping system v2.0."""

from __future__ import annotations

import datetime

from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import Select

from app.core.enums import ShoppingListType
from app.models.shopping import (
    ShoppingList,
    ShoppingProduct,
    ShoppingProductAssignment
)
from app.schemas.shopping import (
    ShoppingListCreate,
    ShoppingListUpdate,
    ShoppingProductCreate,
    ShoppingProductUpdate,
    ShoppingProductAssignmentCreate,
    ShoppingProductAssignmentUpdate,
    ShoppingProductSearchParams,
    ShoppingProductAssignmentSearchParams,
    ShoppingListWithProducts
)
from app.schemas.shopping import ShoppingProductAssignmentRead


# ================================================================== #
# Shopping List CRUD                                                #
# ================================================================== #

def create_shopping_list(db: Session, list_data: ShoppingListCreate) -> ShoppingList:
    """Create a new shopping list.

    Args:
        db: Database session.
        list_data: Validated shopping list data.

    Returns:
        The newly created shopping list.

    Example:
        >>> data = ShoppingListCreate(
        ...     kitchen_id=1,
        ...     name="Weekly Shopping",
        ...     type=ShoppingListType.SUPERMARKET
        ... )
        >>> result = create_shopping_list(db, data)
    """
    db_list = ShoppingList(
        kitchen_id=list_data.kitchen_id,
        name=list_data.name,
        type=list_data.type,
    )

    db.add(db_list)
    db.commit()
    db.refresh(db_list)
    return db_list


def get_shopping_list_by_id(db: Session, list_id: int) -> ShoppingList | None:
    """Get a shopping list by ID.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.

    Returns:
        The shopping list if found, None otherwise.
    """
    return db.scalar(select(ShoppingList).where(ShoppingList.id == list_id))


def get_kitchen_shopping_lists(db: Session, kitchen_id: int) -> list[ShoppingList]:
    """Get all shopping lists for a kitchen.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen.

    Returns:
        A list of shopping lists ordered by creation date.
    """
    query = (
        select(ShoppingList)
        .where(ShoppingList.kitchen_id == kitchen_id)
        .order_by(ShoppingList.created_at.desc())
    )
    return list(db.scalars(query).all())


def update_shopping_list(
        db: Session,
        list_id: int,
        list_data: ShoppingListUpdate
) -> ShoppingList | None:
    """Update a shopping list.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.
        list_data: Validated update data.

    Returns:
        The updated shopping list if found, None otherwise.
    """
    shopping_list = get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        return None

    # Update only provided fields
    update_data = list_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shopping_list, field, value)

    db.commit()
    db.refresh(shopping_list)
    return shopping_list


def delete_shopping_list(db: Session, list_id: int) -> bool:
    """Delete a shopping list.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.

    Returns:
        True if the shopping list was deleted, False if it wasn't found.

    Note:
        This will also delete all product assignments due to cascade.
    """
    shopping_list = get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        return False

    db.delete(shopping_list)
    db.commit()
    return True


def get_shopping_list_with_products(
        db: Session,
        list_id: int
) -> ShoppingListWithProducts | None:
    """Get a shopping list with all assigned products and calculated totals.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.

    Returns:
        Shopping list with products and totals, or None if not found.
    """
    shopping_list = get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        return None

    # Get all assignments for this list
    assignments = get_shopping_list_product_assignments(db, list_id, limit=1000)

    # Calculate totals
    total_products = len(assignments)
    estimated_total = None

    if assignments:
        prices = [
            assignment.shopping_product.estimated_price
            for assignment in assignments
            if assignment.shopping_product.estimated_price is not None
        ]
        if prices:
            estimated_total = sum(prices)

    return ShoppingListWithProducts(
        id=shopping_list.id,
        kitchen_id=shopping_list.kitchen_id,
        name=shopping_list.name,
        type=shopping_list.type,
        created_at=shopping_list.created_at,
        product_assignments=[
            ShoppingProductAssignmentRead.model_validate(assignment, from_attributes=True)
            for assignment in assignments
        ],
        total_products=total_products,
        estimated_total=estimated_total
    )


# ================================================================== #
# Shopping Product CRUD (v2.0)                                      #
# ================================================================== #

def create_shopping_product(
        db: Session,
        product_data: ShoppingProductCreate
) -> ShoppingProduct:
    """Create a new global shopping product.

    Args:
        db: Database session.
        product_data: Validated shopping product data.

    Returns:
        The newly created shopping product.

    Raises:
        ValueError: If food_item or units don't exist.

    Example:
        >>> data = ShoppingProductCreate(
        ...     food_item_id=1,
        ...     package_unit_id=2,  # "pack"
        ...     package_quantity=1.0,
        ...     quantity_in_base_unit=500.0,  # 500g equivalent
        ...     package_type="500 g pack",
        ...     estimated_price=2.99
        ... )
        >>> result = create_shopping_product(db, data)
    """
    # TODO: Add validation that food_item_id and package_unit_id exist
    
    db_product = ShoppingProduct(
        food_item_id=product_data.food_item_id,
        package_unit_id=product_data.package_unit_id,
        package_quantity=product_data.package_quantity,
        quantity_in_base_unit=product_data.quantity_in_base_unit,
        package_type=product_data.package_type,
        estimated_price=product_data.estimated_price,
    )

    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_shopping_product_by_id(db: Session, product_id: int) -> ShoppingProduct | None:
    """Get a shopping product by ID with related objects.

    Args:
        db: Database session.
        product_id: The unique identifier of the shopping product.

    Returns:
        The shopping product with related food_item if found.
    """
    return db.scalar(
        select(ShoppingProduct)
        .options(joinedload(ShoppingProduct.food_item))
        .where(ShoppingProduct.id == product_id)
    )


def get_all_shopping_products(
        db: Session,
        search_params: ShoppingProductSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingProduct]:
    """Get all shopping products with optional filtering.

    Args:
        db: Database session.
        search_params: Optional search parameters.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of shopping products with related objects.
    """
    query: Select = (
        select(ShoppingProduct)
        .options(joinedload(ShoppingProduct.food_item))
        .order_by(ShoppingProduct.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if search_params:
        if search_params.food_item_id is not None:
            query = query.where(ShoppingProduct.food_item_id == search_params.food_item_id)
        if search_params.package_unit_id is not None:
            query = query.where(ShoppingProduct.package_unit_id == search_params.package_unit_id)
        if search_params.min_price is not None:
            query = query.where(ShoppingProduct.estimated_price >= search_params.min_price)
        if search_params.max_price is not None:
            query = query.where(ShoppingProduct.estimated_price <= search_params.max_price)
        if search_params.package_type is not None:
            query = query.where(ShoppingProduct.package_type.ilike(f"%{search_params.package_type}%"))

    return list(db.scalars(query).all())


def update_shopping_product(
        db: Session,
        product_id: int,
        product_data: ShoppingProductUpdate
) -> ShoppingProduct | None:
    """Update a shopping product.

    Args:
        db: Database session.
        product_id: The unique identifier of the shopping product.
        product_data: Validated update data.

    Returns:
        The updated shopping product if found, None otherwise.
    """
    product = get_shopping_product_by_id(db, product_id)
    if product is None:
        return None

    # Update only provided fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    # Update timestamp
    product.last_updated = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(product)
    return product


def delete_shopping_product(db: Session, product_id: int) -> bool:
    """Delete a shopping product.

    Args:
        db: Database session.
        product_id: The unique identifier of the shopping product.

    Returns:
        True if the shopping product was deleted, False if it wasn't found.

    Note:
        This will fail if the product is assigned to any shopping lists
        due to foreign key constraints.
    """
    product = get_shopping_product_by_id(db, product_id)
    if product is None:
        return False

    db.delete(product)
    db.commit()
    return True


# ================================================================== #
# Shopping Product Assignment CRUD (v2.0)                          #
# ================================================================== #

def assign_product_to_list(
        db: Session,
        list_id: int,
        assignment_data: ShoppingProductAssignmentCreate
) -> ShoppingProductAssignment:
    """Assign a shopping product to a shopping list.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        assignment_data: Validated assignment data.

    Returns:
        The newly created assignment.

    Raises:
        ValueError: If assignment already exists or referenced objects don't exist.

    Example:
        >>> data = ShoppingProductAssignmentCreate(
        ...     shopping_product_id=1,
        ...     added_by_user_id=123,
        ...     note="Need this for dinner"
        ... )
        >>> result = assign_product_to_list(db, 1, data)
    """
    # Check if assignment already exists
    existing = get_product_assignment(db, list_id, assignment_data.shopping_product_id)
    if existing:
        raise ValueError("Product already assigned to this list")

    # Verify shopping list exists
    if not get_shopping_list_by_id(db, list_id):
        raise ValueError("Shopping list not found")

    # Verify shopping product exists
    if not get_shopping_product_by_id(db, assignment_data.shopping_product_id):
        raise ValueError("Shopping product not found")

    db_assignment = ShoppingProductAssignment(
        shopping_list_id=list_id,
        shopping_product_id=assignment_data.shopping_product_id,
        added_by_user_id=assignment_data.added_by_user_id,
        is_auto_added=assignment_data.is_auto_added,
        note=assignment_data.note,
    )

    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


def get_product_assignment(
        db: Session,
        list_id: int,
        product_id: int
) -> ShoppingProductAssignment | None:
    """Get a specific product assignment.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        product_id: The ID of the shopping product.

    Returns:
        The assignment if found, None otherwise.
    """
    return db.scalar(
        select(ShoppingProductAssignment)
        .options(
            joinedload(ShoppingProductAssignment.shopping_product)
            .joinedload(ShoppingProduct.food_item)
        )
        .where(
            and_(
                ShoppingProductAssignment.shopping_list_id == list_id,
                ShoppingProductAssignment.shopping_product_id == product_id
            )
        )
    )


def get_shopping_list_product_assignments(
        db: Session,
        list_id: int,
        search_params: ShoppingProductAssignmentSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingProductAssignment]:
    """Get all product assignments for a shopping list.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        search_params: Optional search parameters.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of assignments with related objects.
    """
    query: Select = (
        select(ShoppingProductAssignment)
        .options(
            joinedload(ShoppingProductAssignment.shopping_product)
            .joinedload(ShoppingProduct.food_item)
        )
        .where(ShoppingProductAssignment.shopping_list_id == list_id)
        .order_by(ShoppingProductAssignment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if search_params:
        if search_params.is_auto_added is not None:
            query = query.where(
                ShoppingProductAssignment.is_auto_added == search_params.is_auto_added
            )
        if search_params.added_by_user_id is not None:
            query = query.where(
                ShoppingProductAssignment.added_by_user_id == search_params.added_by_user_id
            )
        if search_params.food_item_id is not None:
            query = query.join(ShoppingProduct).where(
                ShoppingProduct.food_item_id == search_params.food_item_id
            )

    return list(db.scalars(query).all())


def update_product_assignment(
        db: Session,
        list_id: int,
        product_id: int,
        assignment_data: ShoppingProductAssignmentUpdate
) -> ShoppingProductAssignment | None:
    """Update a product assignment.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        product_id: The ID of the shopping product.
        assignment_data: Validated update data.

    Returns:
        The updated assignment if found, None otherwise.
    """
    assignment = get_product_assignment(db, list_id, product_id)
    if assignment is None:
        return None

    # Update only provided fields
    update_data = assignment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assignment, field, value)

    # Update timestamp
    assignment.last_updated = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(assignment)
    return assignment


def remove_product_from_list(db: Session, list_id: int, product_id: int) -> bool:
    """Remove a product assignment from a shopping list.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        product_id: The ID of the shopping product.

    Returns:
        True if the assignment was removed, False if it wasn't found.
    """
    assignment = get_product_assignment(db, list_id, product_id)
    if assignment is None:
        return False

    db.delete(assignment)
    db.commit()
    return True


# ================================================================== #
# Bulk Operations and Utilities                                     #
# ================================================================== #

def get_products_for_food_item(
        db: Session,
        food_item_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingProduct]:
    """Get all shopping products for a specific food item.

    Args:
        db: Database session.
        food_item_id: The ID of the food item.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of shopping products for the food item.
    """
    query = (
        select(ShoppingProduct)
        .options(joinedload(ShoppingProduct.food_item))
        .where(ShoppingProduct.food_item_id == food_item_id)
        .order_by(ShoppingProduct.package_quantity)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(query).all())


def create_product_and_assign_to_list(
        db: Session,
        list_id: int,
        product_data: ShoppingProductCreate,
        assignment_data: ShoppingProductAssignmentCreate
) -> tuple[ShoppingProduct, ShoppingProductAssignment]:
    """Create a new shopping product and immediately assign it to a list.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        product_data: Validated product data.
        assignment_data: Validated assignment data.

    Returns:
        A tuple of (created_product, created_assignment).

    Note:
        This is a convenience function that combines two operations in one transaction.
    """
    # Create the product first
    product = create_shopping_product(db, product_data)

    # Update assignment data with the new product ID
    assignment_data.shopping_product_id = product.id

    # Create the assignment
    assignment = assign_product_to_list(db, list_id, assignment_data)

    return product, assignment


# ================================================================== #
# Unit Conversion Support (Future Implementation)                    #
# ================================================================== #

def calculate_quantity_in_base_unit(
        db: Session,
        food_item_id: int,
        package_unit_id: int,
        package_quantity: float
) -> float:
    """Calculate equivalent quantity in food item's base unit.

    This function converts package quantities to the food item's base unit
    using conversion priorities:
    1. If package unit equals base unit, return quantity unchanged
    2. Look for food-specific conversions in food_item_unit_conversions
    3. Fallback to generic unit conversions
    4. Raise ValueError if no conversion path exists

    Args:
        db: Database session
        food_item_id: Food item ID
        package_unit_id: Package unit ID
        package_quantity: Quantity in package unit

    Returns:
        Equivalent quantity in food item's base unit

    Raises:
        ValueError: If food item not found or no conversion path exists

    Example:
        >>> # Convert 1 pack (500g) to base unit (grams)
        >>> result = calculate_quantity_in_base_unit(db, 1, 2, 1.0)
        >>> # Returns: 500.0
    """
    # Import here to avoid circular imports
    from app.models.food import FoodItem
    from app.models.core import Unit
    from app.crud import food as crud_food
    from app.crud import core as crud_core

    # 1. Get the food item with base_unit_id
    food_item = db.scalar(
        db.query(FoodItem).filter(FoodItem.id == food_item_id)
    )
    if not food_item:
        raise ValueError(f"Food item with ID {food_item_id} not found")

    base_unit_id = food_item.base_unit_id

    # 2. If package unit equals base unit, return quantity unchanged
    if package_unit_id == base_unit_id:
        return package_quantity

    # 3. Check food-specific conversions first (higher priority)
    food_conversion_factor = crud_food.get_conversion_factor_for_food_item(
        db=db,
        food_item_id=food_item_id,
        from_unit_id=package_unit_id,
        to_unit_id=base_unit_id
    )

    if food_conversion_factor is not None:
        return package_quantity * food_conversion_factor

    # 4. Fallback to generic unit conversions
    generic_conversion_factor = crud_core.get_conversion_factor(
        db=db,
        from_unit_id=package_unit_id,
        to_unit_id=base_unit_id
    )

    if generic_conversion_factor is not None:
        return package_quantity * generic_conversion_factor

    # 5. No conversion path found
    # Get unit names for better error message
    package_unit = db.scalar(
        db.query(Unit).filter(Unit.id == package_unit_id)
    )
    base_unit = db.scalar(
        db.query(Unit).filter(Unit.id == base_unit_id)
    )

    package_unit_name = package_unit.name if package_unit else f"ID {package_unit_id}"
    base_unit_name = base_unit.name if base_unit else f"ID {base_unit_id}"

    raise ValueError(
        f"No conversion path found from '{package_unit_name}' to '{base_unit_name}' "
        f"for food item '{food_item.name}' (ID {food_item_id})"
    )
