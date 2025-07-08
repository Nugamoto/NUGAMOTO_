"""CRUD operations for shopping system v2.0 - Schema Returns."""

from __future__ import annotations

import datetime

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql import Select

from app.models.food import FoodItem
from app.models.kitchen import Kitchen
from app.models.shopping import (
    ShoppingList,
    ShoppingProduct,
    ShoppingProductAssignment
)
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
    ShoppingListWithProducts
)


# ================================================================== #
# Helper Functions for Schema Conversion                            #
# ================================================================== #

def build_shopping_list_read(shopping_list_orm: ShoppingList) -> ShoppingListRead:
    """Convert ShoppingList ORM to Read schema."""
    return ShoppingListRead.model_validate(shopping_list_orm, from_attributes=True)


def build_shopping_product_read(product_orm: ShoppingProduct) -> ShoppingProductRead:
    """Convert ShoppingProduct ORM to Read schema."""
    # Build computed fields
    food_item_name = product_orm.food_item.name if product_orm.food_item else "Unknown"

    # Load package unit name via relationship
    package_unit_name = "Unknown"
    if product_orm.package_unit:
        package_unit_name = product_orm.package_unit.name

    # Load base unit name via food_item.base_unit relationship
    base_unit_name = "Unknown"
    if product_orm.food_item and product_orm.food_item.base_unit:
        base_unit_name = product_orm.food_item.base_unit.name

    # Calculate unit price
    unit_price = None
    if product_orm.estimated_price and product_orm.quantity_in_base_unit > 0:
        unit_price = product_orm.estimated_price / product_orm.quantity_in_base_unit

    return ShoppingProductRead(
        id=product_orm.id,
        food_item_id=product_orm.food_item_id,
        package_unit_id=product_orm.package_unit_id,
        package_quantity=product_orm.package_quantity,
        quantity_in_base_unit=product_orm.quantity_in_base_unit,
        package_type=product_orm.package_type,
        estimated_price=product_orm.estimated_price,
        created_at=product_orm.created_at,
        updated_at=product_orm.updated_at,
        food_item_name=food_item_name,
        package_unit_name=package_unit_name,
        base_unit_name=base_unit_name,
        unit_price=unit_price
    )


def build_shopping_product_assignment_read(
        assignment_orm: ShoppingProductAssignment
) -> ShoppingProductAssignmentRead:
    """Convert ShoppingProductAssignment ORM to Read schema."""
    shopping_product = build_shopping_product_read(assignment_orm.shopping_product) \
        if assignment_orm.shopping_product else None

    return ShoppingProductAssignmentRead(
        shopping_list_id=assignment_orm.shopping_list_id,
        shopping_product_id=assignment_orm.shopping_product_id,
        added_by_user_id=assignment_orm.added_by_user_id,
        is_auto_added=assignment_orm.is_auto_added,
        note=assignment_orm.note,
        created_at=assignment_orm.created_at,
        updated_at=assignment_orm.updated_at,
        shopping_product=shopping_product
    )


# ================================================================== #
# Shopping List CRUD - Schema Returns                               #
# ================================================================== #

def create_shopping_list(db: Session, list_data: ShoppingListCreate) -> ShoppingListRead:
    """Create a new shopping list - returns schema.

    Args:
        db: Database session.
        list_data: Validated shopping list data.

    Returns:
        The newly created shopping list schema.

    Raises:
        ValueError: If kitchen doesn't exist.
    """
    # Verify kitchen exists
    kitchen = db.scalar(select(Kitchen).where(Kitchen.id == list_data.kitchen_id))
    if not kitchen:
        raise ValueError("Kitchen not found")
    
    db_list = ShoppingList(
        kitchen_id=list_data.kitchen_id,
        name=list_data.name,
        type=list_data.type,
    )

    db.add(db_list)
    db.commit()
    db.refresh(db_list)

    return build_shopping_list_read(db_list)


def get_shopping_list_by_id(db: Session, list_id: int) -> ShoppingListRead | None:
    """Get a shopping list by ID - returns schema.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.

    Returns:
        The shopping list schema if found, None otherwise.
    """
    shopping_list_orm = db.scalar(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )

    if not shopping_list_orm:
        return None

    return build_shopping_list_read(shopping_list_orm)


def get_kitchen_shopping_lists(db: Session, kitchen_id: int) -> list[ShoppingListRead]:
    """Get all shopping lists for a kitchen - returns schemas.

    Args:
        db: Database session.
        kitchen_id: The ID of the kitchen.

    Returns:
        A list of shopping list schemas ordered by creation date.
    """
    shopping_lists = db.scalars(
        select(ShoppingList)
        .where(ShoppingList.kitchen_id == kitchen_id)
        .order_by(ShoppingList.created_at.desc())
    ).all()

    return [build_shopping_list_read(sl) for sl in shopping_lists]


def update_shopping_list(
        db: Session,
        list_id: int,
        list_data: ShoppingListUpdate
) -> ShoppingListRead | None:
    """Update a shopping list - returns schema.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.
        list_data: Validated update data.

    Returns:
        The updated shopping list schema if found, None otherwise.
    """
    shopping_list_orm = db.scalar(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )

    if not shopping_list_orm:
        return None

    # Update only provided fields
    update_data = list_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shopping_list_orm, field, value)

    db.commit()
    db.refresh(shopping_list_orm)

    return build_shopping_list_read(shopping_list_orm)


def delete_shopping_list(db: Session, list_id: int) -> bool:
    """Delete a shopping list - returns success status.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.

    Returns:
        True if the shopping list was deleted, False if it wasn't found.

    Note:
        This will also delete all product assignments due to cascade.
    """
    shopping_list_orm = db.scalar(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )

    if not shopping_list_orm:
        return False

    db.delete(shopping_list_orm)
    db.commit()
    return True


def get_shopping_list_with_products(
        db: Session,
        list_id: int
) -> ShoppingListWithProducts | None:
    """Get a shopping list with all assigned products and calculated totals - returns schema.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.

    Returns:
        Shopping list with products and totals schema, or None if not found.
    """
    shopping_list_orm = db.scalar(
        select(ShoppingList).where(ShoppingList.id == list_id)
    )

    if not shopping_list_orm:
        return None

    # Get all assignments for this list with related data
    assignments = get_shopping_list_product_assignments(db, list_id, limit=1000)

    # Calculate totals
    total_products = len(assignments)
    estimated_total = None

    if assignments:
        # Get prices from the assignment schemas
        prices = [
            assignment.shopping_product.estimated_price
            for assignment in assignments
            if assignment.shopping_product and assignment.shopping_product.estimated_price is not None
        ]
        if prices:
            estimated_total = sum(prices)

    return ShoppingListWithProducts(
        id=shopping_list_orm.id,
        kitchen_id=shopping_list_orm.kitchen_id,
        name=shopping_list_orm.name,
        type=shopping_list_orm.type,
        created_at=shopping_list_orm.created_at,
        updated_at=shopping_list_orm.updated_at,
        product_assignments=assignments,
        total_products=total_products,
        estimated_total=estimated_total
    )


# ================================================================== #
# Shopping Product CRUD - Schema Returns                            #
# ================================================================== #

def create_shopping_product(
        db: Session,
        product_data: ShoppingProductCreate
) -> ShoppingProductRead:
    """Create a new global shopping product - returns schema.

    Args:
        db: Database session.
        product_data: Validated shopping product data.

    Returns:
        The newly created shopping product schema.

    Raises:
        ValueError: If food_item or units don't exist.
    """
    # Import here to avoid circular imports
    from app.models.food import FoodItem
    from app.models.core import Unit

    # Verify food item exists
    food_item = db.scalar(select(FoodItem).where(FoodItem.id == product_data.food_item_id))
    if not food_item:
        raise ValueError("Food item not found")

    # Verify package unit exists
    package_unit = db.scalar(select(Unit).where(Unit.id == product_data.package_unit_id))
    if not package_unit:
        raise ValueError("Package unit not found")
    
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

    # Load the related data for schema building
    db.refresh(db_product, attribute_names=['food_item', 'package_unit'])
    if db_product.food_item:
        db.refresh(db_product.food_item, attribute_names=['base_unit'])

    return build_shopping_product_read(db_product)


def get_shopping_product_by_id(db: Session, product_id: int) -> ShoppingProductRead | None:
    """Get a shopping product by ID - returns schema.

    Args:
        db: Database session.
        product_id: The unique identifier of the shopping product.

    Returns:
        The shopping product schema if found, None otherwise.
    """
    product_orm = db.scalar(
        select(ShoppingProduct)
        .options(
            selectinload(ShoppingProduct.food_item).selectinload(FoodItem.base_unit),
            selectinload(ShoppingProduct.package_unit)
        )
        .where(ShoppingProduct.id == product_id)
    )

    if not product_orm:
        return None

    return build_shopping_product_read(product_orm)


def get_all_shopping_products(
        db: Session,
        search_params: ShoppingProductSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingProductRead]:
    """Get all shopping products with optional filtering - returns schemas.

    Args:
        db: Database session.
        search_params: Optional search parameters.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of shopping product schemas.
    """
    query: Select = (
        select(ShoppingProduct)
        .options(
            selectinload(ShoppingProduct.food_item).selectinload(FoodItem.base_unit),
            selectinload(ShoppingProduct.package_unit)
        )
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

    products = db.scalars(query).all()
    return [build_shopping_product_read(product) for product in products]


def update_shopping_product(
        db: Session,
        product_id: int,
        product_data: ShoppingProductUpdate
) -> ShoppingProductRead | None:
    """Update a shopping product - returns schema.

    Args:
        db: Database session.
        product_id: The unique identifier of the shopping product.
        product_data: Validated update data.

    Returns:
        The updated shopping product schema if found, None otherwise.
    """
    product_orm = db.scalar(
        select(ShoppingProduct)
        .options(
            selectinload(ShoppingProduct.food_item).selectinload(FoodItem.base_unit),
            selectinload(ShoppingProduct.package_unit)
        )
        .where(ShoppingProduct.id == product_id)
    )

    if not product_orm:
        return None

    # Update only provided fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product_orm, field, value)

    # Update timestamp
    product_orm.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(product_orm)

    return build_shopping_product_read(product_orm)


def delete_shopping_product(db: Session, product_id: int) -> bool:
    """Delete a shopping product - returns success status.

    Args:
        db: Database session.
        product_id: The unique identifier of the shopping product.

    Returns:
        True if the shopping product was deleted, False if it wasn't found.

    Note:
        This will fail if the product is assigned to any shopping lists
        due to foreign key constraints.
    """
    product_orm = db.scalar(
        select(ShoppingProduct).where(ShoppingProduct.id == product_id)
    )

    if not product_orm:
        return False

    # Check if product is assigned to any lists
    assignment_count = db.scalar(
        select(func.count(ShoppingProductAssignment.shopping_list_id))
        .where(ShoppingProductAssignment.shopping_product_id == product_id)
    )

    if assignment_count > 0:
        raise ValueError(f"Cannot delete product that is assigned to {assignment_count} shopping list(s)")

    db.delete(product_orm)
    db.commit()
    return True


# ================================================================== #
# Shopping Product Assignment CRUD - Schema Returns                 #
# ================================================================== #

def assign_product_to_list(
        db: Session,
        list_id: int,
        assignment_data: ShoppingProductAssignmentCreate
) -> ShoppingProductAssignmentRead:
    """Assign a shopping product to a shopping list - returns schema.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        assignment_data: Validated assignment data.

    Returns:
        The newly created assignment schema.

    Raises:
        ValueError: If assignment already exists or referenced objects don't exist.
    """
    # Check if assignment already exists
    existing = get_product_assignment_orm(db, list_id, assignment_data.shopping_product_id)
    if existing:
        raise ValueError("Product already assigned to this list")

    # Verify shopping list exists
    shopping_list = db.scalar(select(ShoppingList).where(ShoppingList.id == list_id))
    if not shopping_list:
        raise ValueError("Shopping list not found")

    # Verify shopping product exists
    shopping_product = db.scalar(
        select(ShoppingProduct).where(ShoppingProduct.id == assignment_data.shopping_product_id)
    )
    if not shopping_product:
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

    # Load related data for schema building with full relationships
    db.refresh(db_assignment, attribute_names=['shopping_product'])
    if db_assignment.shopping_product:
        db.refresh(db_assignment.shopping_product, attribute_names=['food_item', 'package_unit'])
        if db_assignment.shopping_product.food_item:
            db.refresh(db_assignment.shopping_product.food_item, attribute_names=['base_unit'])

    return build_shopping_product_assignment_read(db_assignment)


def get_product_assignment(
        db: Session,
        list_id: int,
        product_id: int
) -> ShoppingProductAssignmentRead | None:
    """Get a specific product assignment - returns schema.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        product_id: The ID of the shopping product.

    Returns:
        The assignment schema if found, None otherwise.
    """
    assignment_orm = get_product_assignment_orm(db, list_id, product_id)

    if not assignment_orm:
        return None

    return build_shopping_product_assignment_read(assignment_orm)


def get_shopping_list_product_assignments(
        db: Session,
        list_id: int,
        search_params: ShoppingProductAssignmentSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingProductAssignmentRead]:
    """Get all product assignments for a shopping list - returns schemas.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        search_params: Optional search parameters.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of assignment schemas.
    """
    query: Select = (
        select(ShoppingProductAssignment)
        .options(
            selectinload(ShoppingProductAssignment.shopping_product)
            .selectinload(ShoppingProduct.food_item)
            .selectinload(FoodItem.base_unit),
            selectinload(ShoppingProductAssignment.shopping_product)
            .selectinload(ShoppingProduct.package_unit)
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

    assignments = db.scalars(query).all()
    return [build_shopping_product_assignment_read(assignment) for assignment in assignments]


def update_product_assignment(
        db: Session,
        list_id: int,
        product_id: int,
        assignment_data: ShoppingProductAssignmentUpdate
) -> ShoppingProductAssignmentRead | None:
    """Update a product assignment - returns schema.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        product_id: The ID of the shopping product.
        assignment_data: Validated update data.

    Returns:
        The updated assignment schema if found, None otherwise.
    """
    assignment_orm = get_product_assignment_orm_with_relationships(db, list_id, product_id)

    if not assignment_orm:
        return None

    # Update only provided fields
    update_data = assignment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(assignment_orm, field, value)

    # Update timestamp
    assignment_orm.updated_at = datetime.datetime.now(datetime.timezone.utc)

    db.commit()
    db.refresh(assignment_orm)

    return build_shopping_product_assignment_read(assignment_orm)


def remove_product_from_list(db: Session, list_id: int, product_id: int) -> bool:
    """Remove a product assignment from a shopping list - returns success status.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        product_id: The ID of the shopping product.

    Returns:
        True if the assignment was removed, False if it wasn't found.
    """
    assignment_orm = get_product_assignment_orm(db, list_id, product_id)

    if not assignment_orm:
        return False

    db.delete(assignment_orm)
    db.commit()
    return True


# ================================================================== #
# Bulk Operations and Utilities - Schema Returns                    #
# ================================================================== #

def get_products_for_food_item(
        db: Session,
        food_item_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingProductRead]:
    """Get all shopping products for a specific food item - returns schemas.

    Args:
        db: Database session.
        food_item_id: The ID of the food item.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of shopping product schemas for the food item.
    """
    products = db.scalars(
        select(ShoppingProduct)
        .options(
            selectinload(ShoppingProduct.food_item).selectinload(FoodItem.base_unit),
            selectinload(ShoppingProduct.package_unit)
        )
        .where(ShoppingProduct.food_item_id == food_item_id)
        .order_by(ShoppingProduct.package_quantity)
        .offset(skip)
        .limit(limit)
    ).all()

    return [build_shopping_product_read(product) for product in products]


def create_product_and_assign_to_list(
        db: Session,
        list_id: int,
        product_data: ShoppingProductCreate,
        assignment_data: ShoppingProductAssignmentCreate
) -> tuple[ShoppingProductRead, ShoppingProductAssignmentRead]:
    """Create a new shopping product and immediately assign it to a list - returns schemas.

    Args:
        db: Database session.
        list_id: The ID of the shopping list.
        product_data: Validated product data.
        assignment_data: Validated assignment data.

    Returns:
        A tuple of (created_product_schema, created_assignment_schema).

    Note:
        This is a convenience function that combines two operations in one transaction.
    """
    # Create the product first
    product_schema = create_shopping_product(db, product_data)

    # Update assignment data with the new product ID
    assignment_data.shopping_product_id = product_schema.id

    # Create the assignment
    assignment_schema = assign_product_to_list(db, list_id, assignment_data)

    return product_schema, assignment_schema


# ================================================================== #
# ORM Helper Functions (for internal use)                           #
# ================================================================== #

def get_shopping_list_orm_by_id(db: Session, list_id: int) -> ShoppingList | None:
    """Get ShoppingList ORM object by ID - for internal use."""
    return db.scalar(select(ShoppingList).where(ShoppingList.id == list_id))


def get_shopping_product_orm_by_id(db: Session, product_id: int) -> ShoppingProduct | None:
    """Get ShoppingProduct ORM object by ID - for internal use."""
    return db.scalar(
        select(ShoppingProduct)
        .options(selectinload(ShoppingProduct.food_item))
        .where(ShoppingProduct.id == product_id)
    )


def get_product_assignment_orm(
        db: Session,
        list_id: int,
        product_id: int
) -> ShoppingProductAssignment | None:
    """Get ShoppingProductAssignment ORM object - for internal use."""
    return db.scalar(
        select(ShoppingProductAssignment)
        .options(
            selectinload(ShoppingProductAssignment.shopping_product)
            .selectinload(ShoppingProduct.food_item)
        )
        .where(
            and_(
                ShoppingProductAssignment.shopping_list_id == list_id,
                ShoppingProductAssignment.shopping_product_id == product_id
            )
        )
    )


def get_product_assignment_orm_with_relationships(
        db: Session,
        list_id: int,
        product_id: int
) -> ShoppingProductAssignment | None:
    """Get ShoppingProductAssignment ORM object with full relationships - for internal use."""
    return db.scalar(
        select(ShoppingProductAssignment)
        .options(
            selectinload(ShoppingProductAssignment.shopping_product)
            .selectinload(ShoppingProduct.food_item)
            .selectinload(FoodItem.base_unit),
            selectinload(ShoppingProductAssignment.shopping_product)
            .selectinload(ShoppingProduct.package_unit)
        )
        .where(
            and_(
                ShoppingProductAssignment.shopping_list_id == list_id,
                ShoppingProductAssignment.shopping_product_id == product_id
            )
        )
    )


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
    """
    # Import here to avoid circular imports
    from app.models.inventory import FoodItem
    from app.models.core import Unit
    from app.crud import food as crud_food
    from app.crud import core as crud_core

    # 1. Get the food item with base_unit_id
    food_item = db.scalar(
        select(FoodItem).where(FoodItem.id == food_item_id)
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
    package_unit = db.scalar(select(Unit).where(Unit.id == package_unit_id))
    base_unit = db.scalar(select(Unit).where(Unit.id == base_unit_id))

    package_unit_name = package_unit.name if package_unit else f"ID {package_unit_id}"
    base_unit_name = base_unit.name if base_unit else f"ID {base_unit_id}"

    raise ValueError(
        f"No conversion path found from '{package_unit_name}' to '{base_unit_name}' "
        f"for food item '{food_item.name}' (ID {food_item_id})"
    )