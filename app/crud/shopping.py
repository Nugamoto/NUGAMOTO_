"""CRUD operations for shopping system."""

from __future__ import annotations

from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import Select

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
)


# ================================================================== #
# Shopping List CRUD                                                #
# ================================================================== #

def create_shopping_list(db: Session, list_data: ShoppingListCreate) -> ShoppingList:
    """Create a new shopping list."""
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
    """Get a shopping list by ID."""
    stmt = select(ShoppingList).where(ShoppingList.id == list_id)
    return db.scalar(stmt)


def get_kitchen_shopping_lists(db: Session, kitchen_id: int) -> list[ShoppingList]:
    """Get all shopping lists for a kitchen."""
    stmt = select(ShoppingList).where(ShoppingList.kitchen_id == kitchen_id)
    return list(db.scalars(stmt).all())


def update_shopping_list(
        db: Session,
        list_id: int,
        list_data: ShoppingListUpdate
) -> ShoppingList:
    """Update a shopping list."""
    shopping_list = get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        raise ValueError("Shopping list not found")

    if list_data.name is not None:
        shopping_list.name = list_data.name
    if list_data.type is not None:
        shopping_list.type = list_data.type

    db.commit()
    db.refresh(shopping_list)
    return shopping_list


def delete_shopping_list(db: Session, list_id: int) -> None:
    """Delete a shopping list."""
    shopping_list = get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        raise ValueError("Shopping list not found")

    db.delete(shopping_list)
    db.commit()


# ================================================================== #
# Shopping Product CRUD                                             #
# ================================================================== #

def create_shopping_product(
        db: Session,
        product_data: ShoppingProductCreate
) -> ShoppingProduct:
    """Create a new global shopping product."""
    db_product = ShoppingProduct(
        food_item_id=product_data.food_item_id,
        unit=product_data.unit,
        quantity=product_data.quantity,
        package_type=product_data.package_type,
        estimated_price=product_data.estimated_price,
    )

    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def get_shopping_product_by_id(db: Session, product_id: int) -> ShoppingProduct | None:
    """Get a shopping product by ID with food item details."""
    stmt = (
        select(ShoppingProduct)
        .options(joinedload(ShoppingProduct.food_item))
        .where(ShoppingProduct.id == product_id)
    )
    return db.scalar(stmt)


def get_all_shopping_products(
        db: Session,
        search_params: ShoppingProductSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingProduct]:
    """Get all shopping products with optional filtering."""
    stmt: Select = (
        select(ShoppingProduct)
        .options(joinedload(ShoppingProduct.food_item))
        .offset(skip)
        .limit(limit)
    )

    if search_params:
        if search_params.food_item_id is not None:
            stmt = stmt.where(ShoppingProduct.food_item_id == search_params.food_item_id)
        if search_params.package_type is not None:
            stmt = stmt.where(ShoppingProduct.package_type == search_params.package_type)
        if search_params.min_price is not None:
            stmt = stmt.where(ShoppingProduct.estimated_price >= search_params.min_price)
        if search_params.max_price is not None:
            stmt = stmt.where(ShoppingProduct.estimated_price <= search_params.max_price)
        if search_params.unit is not None:
            stmt = stmt.where(ShoppingProduct.unit == search_params.unit)

    return list(db.scalars(stmt).all())


def update_shopping_product(
        db: Session,
        product_id: int,
        product_data: ShoppingProductUpdate
) -> ShoppingProduct:
    """Update a shopping product."""
    product = get_shopping_product_by_id(db, product_id)
    if product is None:
        raise ValueError("Shopping product not found")

    if product_data.unit is not None:
        product.unit = product_data.unit
    if product_data.quantity is not None:
        product.quantity = product_data.quantity
    if product_data.package_type is not None:
        product.package_type = product_data.package_type
    if product_data.estimated_price is not None:
        product.estimated_price = product_data.estimated_price

    db.commit()
    db.refresh(product)
    return product


def delete_shopping_product(db: Session, product_id: int) -> None:
    """Delete a shopping product."""
    product = get_shopping_product_by_id(db, product_id)
    if product is None:
        raise ValueError("Shopping product not found")

    db.delete(product)
    db.commit()


# ================================================================== #
# Shopping Product Assignment CRUD                                  #
# ================================================================== #

def assign_product_to_list(
        db: Session,
        list_id: int,
        assignment_data: ShoppingProductAssignmentCreate
) -> ShoppingProductAssignment:
    """Assign a shopping product to a shopping list."""
    # Check if assignment already exists
    existing = get_product_assignment(
        db, list_id, assignment_data.shopping_product_id
    )
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
    """Get a specific product assignment."""
    stmt = (
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
    return db.scalar(stmt)


def get_shopping_list_product_assignments(
        db: Session,
        list_id: int,
        search_params: ShoppingProductAssignmentSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingProductAssignment]:
    """Get all product assignments for a shopping list."""
    stmt: Select = (
        select(ShoppingProductAssignment)
        .options(
            joinedload(ShoppingProductAssignment.shopping_product)
            .joinedload(ShoppingProduct.food_item)
        )
        .where(ShoppingProductAssignment.shopping_list_id == list_id)
        .offset(skip)
        .limit(limit)
    )

    if search_params:
        if search_params.is_auto_added is not None:
            stmt = stmt.where(
                ShoppingProductAssignment.is_auto_added == search_params.is_auto_added
            )
        if search_params.added_by_user_id is not None:
            stmt = stmt.where(
                ShoppingProductAssignment.added_by_user_id == search_params.added_by_user_id
            )
        if search_params.food_item_id is not None:
            stmt = stmt.join(ShoppingProduct).where(
                ShoppingProduct.food_item_id == search_params.food_item_id
            )
        if search_params.package_type is not None:
            stmt = stmt.join(ShoppingProduct).where(
                ShoppingProduct.package_type == search_params.package_type
            )

    return list(db.scalars(stmt).all())


def update_product_assignment(
        db: Session,
        list_id: int,
        product_id: int,
        assignment_data: ShoppingProductAssignmentUpdate
) -> ShoppingProductAssignment:
    """Update a product assignment."""
    assignment = get_product_assignment(db, list_id, product_id)
    if assignment is None:
        raise ValueError("Product assignment not found")

    if assignment_data.note is not None:
        assignment.note = assignment_data.note

    db.commit()
    db.refresh(assignment)
    return assignment


def remove_product_from_list(db: Session, list_id: int, product_id: int) -> None:
    """Remove a product assignment from a shopping list."""
    assignment = get_product_assignment(db, list_id, product_id)
    if assignment is None:
        raise ValueError("Product assignment not found")

    db.delete(assignment)
    db.commit()
