"""CRUD operations for shopping list functionality."""

from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session, selectinload

from app.models.shopping import ShoppingList, ShoppingListItem, ShoppingListType, PackageType
from app.schemas.shopping import (
    ShoppingListCreate,
    ShoppingListUpdate,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListItemSearchParams,
    ShoppingListSummary
)


# ------------------------------------------------------------------ #
# Shopping List CRUD                                                 #
# ------------------------------------------------------------------ #

def create_shopping_list(db: Session, list_data: ShoppingListCreate) -> ShoppingList:
    """Create a new shopping list.

    Args:
        db: Database session.
        list_data: Validated shopping list data.

    Returns:
        The newly created shopping list.

    Example:
        >>> data = ShoppingListCreate(
        ...     kitchen_id=123,
        ...     name="Edeka Einkauf",
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
    """Retrieve a shopping list by its ID.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.

    Returns:
        The shopping list if found, None otherwise.

    Example:
        >>> shopping_list = get_shopping_list_by_id(db, 123)
        >>> if shopping_list:
        ...     print(f"Found list: {shopping_list.name}")
    """
    return db.scalar(select(ShoppingList).where(ShoppingList.id == list_id))


def get_shopping_list_with_items(db: Session, list_id: int) -> ShoppingList | None:
    """Retrieve a shopping list with all its items.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.

    Returns:
        The shopping list with items loaded, or None if not found.

    Example:
        >>> shopping_list = get_shopping_list_with_items(db, 123)
        >>> if shopping_list:
        ...     print(f"List has {len(shopping_list.items)} items")
    """
    return db.scalar(
        select(ShoppingList)
        .options(selectinload(ShoppingList.items))
        .where(ShoppingList.id == list_id)
    )


def get_shopping_lists_by_kitchen(
        db: Session, kitchen_id: int, skip: int = 0, limit: int = 100
) -> list[ShoppingList]:
    """Retrieve all shopping lists for a specific kitchen.

    Args:
        db: Database session.
        kitchen_id: The kitchen ID to filter by.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        A list of shopping lists for the kitchen, ordered by creation time (newest first).

    Example:
        >>> lists = get_shopping_lists_by_kitchen(db, kitchen_id=123, skip=0, limit=10)
        >>> for shopping_list in lists:
        ...     print(f"List: {shopping_list.name}")
    """
    query = (
        select(ShoppingList)
        .where(ShoppingList.kitchen_id == kitchen_id)
        .order_by(ShoppingList.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(query).all())


def update_shopping_list(
        db: Session, list_id: int, list_data: ShoppingListUpdate
) -> ShoppingList | None:
    """Update an existing shopping list.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list.
        list_data: Validated update data.

    Returns:
        The updated shopping list if found, None otherwise.

    Example:
        >>> data = ShoppingListUpdate(name="Updated List Name")
        >>> updated = update_shopping_list(db, 123, data)
    """
    shopping_list = get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        return None

    if list_data.name is not None:
        shopping_list.name = list_data.name
    if list_data.type is not None:
        shopping_list.type = list_data.type

    db.commit()
    db.refresh(shopping_list)
    return shopping_list


def delete_shopping_list(db: Session, list_id: int) -> bool:
    """Delete a shopping list by its ID.

    Args:
        db: Database session.
        list_id: The unique identifier of the shopping list to delete.

    Returns:
        True if the list was deleted, False if it wasn't found.

    Example:
        >>> success = delete_shopping_list(db, 123)
        >>> if success:
        ...     print("Shopping list deleted successfully")
    """
    shopping_list = get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        return False

    db.delete(shopping_list)
    db.commit()
    return True


# ------------------------------------------------------------------ #
# Shopping List Item CRUD                                            #
# ------------------------------------------------------------------ #

def create_shopping_list_item(
        db: Session, list_id: int, item_data: ShoppingListItemCreate
) -> ShoppingListItem:
    """Create a new shopping list item.

    Args:
        db: Database session.
        list_id: The shopping list ID.
        item_data: Validated shopping list item data.

    Returns:
        The newly created shopping list item.

    Raises:
        ValueError: If the shopping list doesn't exist.

    Example:
        >>> data = ShoppingListItemCreate(
        ...     food_item_id=456,
        ...     quantity=2.5,
        ...     unit="kg",
        ...     package_type=PackageType.LOOSE,
        ...     estimated_price=3.50
        ... )
        >>> result = create_shopping_list_item(db, list_id=123, item_data=data)
    """
    # Verify shopping list exists
    shopping_list = get_shopping_list_by_id(db, list_id)
    if shopping_list is None:
        raise ValueError("Shopping list not found")

    db_item = ShoppingListItem(
        shopping_list_id=list_id,
        food_item_id=item_data.food_item_id,
        quantity=item_data.quantity,
        unit=item_data.unit,
        package_type=item_data.package_type,
        estimated_price=item_data.estimated_price,
        is_auto_added=item_data.is_auto_added,
        added_by_user_id=item_data.added_by_user_id,
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return db_item


def get_shopping_list_item_by_id(db: Session, item_id: int) -> ShoppingListItem | None:
    """Retrieve a shopping list item by its ID.

    Args:
        db: Database session.
        item_id: The unique identifier of the shopping list item.

    Returns:
        The shopping list item if found, None otherwise.

    Example:
        >>> item = get_shopping_list_item_by_id(db, 456)
        >>> if item:
        ...     print(f"Item quantity: {item.quantity} {item.unit}")
    """
    return db.scalar(select(ShoppingListItem).where(ShoppingListItem.id == item_id))


def get_shopping_list_items(
        db: Session,
        list_id: int,
        search_params: ShoppingListItemSearchParams,
        skip: int = 0,
        limit: int = 100
) -> list[ShoppingListItem]:
    """Retrieve shopping list items with optional filtering.

    Args:
        db: Database session.
        list_id: The shopping list ID to filter by.
        search_params: Search and filter parameters.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        A list of shopping list items matching the criteria, ordered by creation time.

    Example:
        >>> params = ShoppingListItemSearchParams(
        ...     is_auto_added=False,
        ...     added_by_user_id=789
        ... )
        >>> items = get_shopping_list_items(db, list_id=123, search_params=params)
    """
    query = select(ShoppingListItem).where(ShoppingListItem.shopping_list_id == list_id)

    # Apply filters
    if search_params.is_auto_added is not None:
        query = query.where(ShoppingListItem.is_auto_added == search_params.is_auto_added)

    if search_params.added_by_user_id:
        query = query.where(ShoppingListItem.added_by_user_id == search_params.added_by_user_id)

    if search_params.food_item_id:
        query = query.where(ShoppingListItem.food_item_id == search_params.food_item_id)

    if search_params.package_type:
        query = query.where(ShoppingListItem.package_type == search_params.package_type)

    if search_params.min_price is not None:
        query = query.where(ShoppingListItem.estimated_price >= search_params.min_price)

    if search_params.max_price is not None:
        query = query.where(ShoppingListItem.estimated_price <= search_params.max_price)

    # Order by creation time and apply pagination
    query = query.order_by(ShoppingListItem.created_at.asc()).offset(skip).limit(limit)

    return list(db.scalars(query).all())


def update_shopping_list_item(
        db: Session, item_id: int, item_data: ShoppingListItemUpdate
) -> ShoppingListItem | None:
    """Update an existing shopping list item.

    Args:
        db: Database session.
        item_id: The unique identifier of the shopping list item.
        item_data: Validated update data.

    Returns:
        The updated shopping list item if found, None otherwise.

    Example:
        >>> data = ShoppingListItemUpdate(quantity=5.0, estimated_price=7.25)
        >>> updated = update_shopping_list_item(db, 456, data)
    """
    item = get_shopping_list_item_by_id(db, item_id)
    if item is None:
        return None

    if item_data.quantity is not None:
        item.quantity = item_data.quantity
    if item_data.unit is not None:
        item.unit = item_data.unit
    if item_data.package_type is not None:
        item.package_type = item_data.package_type
    if item_data.estimated_price is not None:
        item.estimated_price = item_data.estimated_price
    if item_data.is_auto_added is not None:
        item.is_auto_added = item_data.is_auto_added
    if item_data.added_by_user_id is not None:
        item.added_by_user_id = item_data.added_by_user_id

    db.commit()
    db.refresh(item)
    return item


def delete_shopping_list_item(db: Session, item_id: int) -> bool:
    """Delete a shopping list item by its ID.

    Args:
        db: Database session.
        item_id: The unique identifier of the shopping list item to delete.

    Returns:
        True if the item was deleted, False if it wasn't found.

    Example:
        >>> success = delete_shopping_list_item(db, 456)
        >>> if success:
        ...     print("Item deleted successfully")
    """
    item = get_shopping_list_item_by_id(db, item_id)
    if item is None:
        return False

    db.delete(item)
    db.commit()
    return True


def get_or_create_shopping_list_item(
        db: Session, list_id: int, food_item_id: int, item_data: ShoppingListItemCreate
) -> tuple[ShoppingListItem, bool]:
    """Get an existing item or create a new one if it doesn't exist.

    Args:
        db: Database session.
        list_id: The shopping list ID.
        food_item_id: The food item ID.
        item_data: Validated shopping list item data.

    Returns:
        A tuple of (item, created) where created is True if a new item was created.

    Example:
        >>> data = ShoppingListItemCreate(...)
        >>> item, created = get_or_create_shopping_list_item(db, 123, 456, data)
        >>> if created:
        ...     print("New item created")
        ... else:
        ...     print("Existing item found")
    """
    # Check if item already exists
    existing_item = db.scalar(
        select(ShoppingListItem).where(
            and_(
                ShoppingListItem.shopping_list_id == list_id,
                ShoppingListItem.food_item_id == food_item_id
            )
        )
    )

    if existing_item:
        return existing_item, False

    # Create new item
    new_item = create_shopping_list_item(db, list_id, item_data)
    return new_item, True


def get_shopping_summary(db: Session, kitchen_id: int | None = None) -> ShoppingListSummary:
    """Get summary statistics for shopping lists.

    Args:
        db: Database session.
        kitchen_id: Optional kitchen ID to filter by.

    Returns:
        Summary statistics including counts and estimated values.

    Example:
        >>> summary = get_shopping_summary(db, kitchen_id=123)
        >>> print(f"Total lists: {summary.total_lists}")
    """
    # Base query for shopping lists
    lists_query = select(ShoppingList)
    if kitchen_id:
        lists_query = lists_query.where(ShoppingList.kitchen_id == kitchen_id)

    # Base query for items
    items_query = select(ShoppingListItem)
    if kitchen_id:
        items_query = items_query.join(ShoppingList).where(ShoppingList.kitchen_id == kitchen_id)

    # Count total lists
    total_lists = db.scalar(select(func.count()).select_from(lists_query.subquery())) or 0

    # Count total items
    total_items = db.scalar(select(func.count()).select_from(items_query.subquery())) or 0

    # Count by shopping list type
    type_counts = db.execute(
        select(ShoppingList.type, func.count(ShoppingList.id))
        .group_by(ShoppingList.type)
    ).all()
    items_by_type = {str(list_type): count for list_type, count in type_counts}

    # Count auto vs manual items
    auto_added_items = db.scalar(
        items_query.where(ShoppingListItem.is_auto_added == True)
        .with_only_columns(func.count())
    ) or 0

    manual_items = total_items - auto_added_items

    # Calculate total estimated value
    total_estimated_value = db.scalar(
        items_query.with_only_columns(func.sum(ShoppingListItem.estimated_price))
    ) or 0.0

    return ShoppingListSummary(
        total_lists=total_lists,
        total_items=total_items,
        items_by_type=items_by_type,
        auto_added_items=auto_added_items,
        manual_items=manual_items,
        total_estimated_value=total_estimated_value,
    )
