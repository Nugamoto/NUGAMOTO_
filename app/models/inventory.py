"""SQLAlchemy ORM models for inventory management."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base

# Import settings at module level (füge das oben hinzu)
EXPIRING_ITEMS_THRESHOLD_DAYS = settings.expiring_items_threshold_days

if TYPE_CHECKING:
    from app.models.kitchen import Kitchen


class FoodItem(Base):
    """Represents a row in the ``food_items`` table.

    Food items are global entities that can be used across all kitchens.
    They represent basic food categories like "Tomato", "Rice", etc.
    """

    __tablename__ = "food_items"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="piece")

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    inventory_items: Mapped[list[InventoryItem]] = relationship(
        "InventoryItem", back_populates="food_item"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"FoodItem(id={self.id!r}, name={self.name!r}, "
            f"category={self.category!r}, unit={self.unit!r})"
        )


class StorageLocation(Base):
    """Represents a row in the ``storage_locations`` table.

    Storage locations are kitchen-specific places where food can be stored,
    such as "Fridge", "Pantry", "Freezer", etc.
    """

    __tablename__ = "storage_locations"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kitchen_id: Mapped[int] = mapped_column(
        ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    kitchen: Mapped[Kitchen] = relationship("Kitchen")
    inventory_items: Mapped[list[InventoryItem]] = relationship(
        "InventoryItem", back_populates="storage_location"
    )

    # ------------------------------------------------------------------ #
    # Constraints                                                         #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint("kitchen_id", "name", name="uq_kitchen_storage_name"),
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"StorageLocation(id={self.id!r}, kitchen_id={self.kitchen_id!r}, "
            f"name={self.name!r})"
        )


class InventoryItem(Base):
    """Represents a row in the ``inventory_items`` table.

    Inventory items link kitchens, food items, and storage locations together
    with quantity and expiration information. This is where the actual inventory
    data is stored.

    Note: min_quantity can be used later by AI services to automatically
    generate shopping lists when items run low.
    """

    __tablename__ = "inventory_items"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kitchen_id: Mapped[int] = mapped_column(
        ForeignKey("kitchens.id", ondelete="CASCADE"), nullable=False
    )
    food_item_id: Mapped[int] = mapped_column(
        ForeignKey("food_items.id", ondelete="CASCADE"), nullable=False
    )
    storage_location_id: Mapped[int] = mapped_column(
        ForeignKey("storage_locations.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(nullable=False, default=0.0)
    min_quantity: Mapped[float | None] = mapped_column(default=None)
    expiration_date: Mapped[datetime.date | None] = mapped_column(Date, default=None)

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    kitchen: Mapped[Kitchen] = relationship("Kitchen")
    food_item: Mapped[FoodItem] = relationship("FoodItem", back_populates="inventory_items")
    storage_location: Mapped[StorageLocation] = relationship(
        "StorageLocation", back_populates="inventory_items"
    )

    # ------------------------------------------------------------------ #
    # Constraints                                                         #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint(
            "kitchen_id", "food_item_id", "storage_location_id",
            name="uq_kitchen_food_storage"
        ),
    )

    # ------------------------------------------------------------------ #
    # Properties                                                          #
    # ------------------------------------------------------------------ #
    @property
    def is_low_stock(self) -> bool:
        """Check if this item is below minimum quantity threshold.

        Returns:
            True if quantity is below min_quantity, False otherwise.
            Returns False if min_quantity is not set.

        Note:
            This property can be used by AI services to identify items
            that should be added to shopping lists.
        """
        if self.min_quantity is None:
            return False
        return self.quantity < self.min_quantity

    @property
    def is_expired(self) -> bool:
        """Check if this item has expired.

        Returns:
            True if expiration_date is in the past, False otherwise.
            Returns False if expiration_date is not set.
        """
        if self.expiration_date is None:
            return False
        return self.expiration_date < datetime.date.today()

    @property
    def expires_soon(self, days: int = EXPIRING_ITEMS_THRESHOLD_DAYS) -> bool:
        """Check if this item expires within the specified number of days.

        Args:
            days: Number of days to check ahead (default: from settings).

        Returns:
            True if expiration_date is within the specified days, False otherwise.
            Returns False if expiration_date is not set.
        """
        if self.expiration_date is None:
            return False
        threshold_date = datetime.date.today() + datetime.timedelta(days=days)
        return self.expiration_date <= threshold_date

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"InventoryItem(id={self.id!r}, kitchen_id={self.kitchen_id!r}, "
            f"food_item_id={self.food_item_id!r}, quantity={self.quantity!r})"
        )