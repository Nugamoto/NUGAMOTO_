"""SQLAlchemy ORM models for inventory management."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date, DateTime, Float, ForeignKey, String, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.config import settings
from backend.db.base import Base
from backend.models.food import FoodItem

if TYPE_CHECKING:
    from backend.models.kitchen import Kitchen

# Threshold for considering items as "expiring soon" (in days)
EXPIRING_ITEMS_THRESHOLD_DAYS = settings.expiring_items_threshold_days


class StorageLocation(Base):
    """Represents a row in the ``storage_locations`` table.

    Storage locations are specific areas within a kitchen where
    inventory items can be stored (e.g., "Refrigerator", "Pantry", "Freezer").
    """

    __tablename__ = "storage_locations"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kitchen_id: Mapped[int] = mapped_column(
        ForeignKey("kitchens.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Name of the storage location (e.g., 'Refrigerator', 'Pantry')"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    kitchen: Mapped[Kitchen] = relationship(
        "Kitchen",
        back_populates="storage_locations"
    )
    inventory_items: Mapped[list[InventoryItem]] = relationship(
        "InventoryItem",
        back_populates="storage_location",
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Table Constraints                                                   #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint(
            'kitchen_id', 'name',
            name='uq_storage_location_kitchen_name'
        ),
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

    Inventory items track specific food items within a kitchen's storage locations.
    Each item has a quantity stored in the food item's base unit and optional
    minimum quantity thresholds and expiration dates.
    """

    __tablename__ = "inventory_items"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kitchen_id: Mapped[int] = mapped_column(
        ForeignKey("kitchens.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    food_item_id: Mapped[int] = mapped_column(
        ForeignKey("food_items.id"),
        nullable=False,
        index=True,
        comment="Reference to the food item being stored"
    )
    storage_location_id: Mapped[int] = mapped_column(
        ForeignKey("storage_locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Where this item is stored within the kitchen"
    )
    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Current quantity in the food item's base unit"
    )
    min_quantity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Minimum quantity threshold for low stock alerts"
    )
    expiration_date: Mapped[datetime.date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Expiration date of this specific inventory item"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    kitchen: Mapped[Kitchen] = relationship(
        "Kitchen",
        back_populates="inventory_items"
    )
    food_item: Mapped[FoodItem] = relationship(
        "FoodItem",
        back_populates="inventory_items"
    )
    storage_location: Mapped[StorageLocation] = relationship(
        "StorageLocation",
        back_populates="inventory_items"
    )

    # ------------------------------------------------------------------ #
    # Table Constraints                                                   #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint(
            'kitchen_id', 'food_item_id', 'storage_location_id',
            name='uq_inventory_item_kitchen_food_storage'
        ),
    )

    # ------------------------------------------------------------------ #
    # Business Logic Methods                                              #
    # ------------------------------------------------------------------ #
    def is_low_stock(self) -> bool:
        """Check if this inventory item is below its minimum quantity threshold.

        Returns:
            True if quantity is below min_quantity, False otherwise.
            If min_quantity is not set, returns False.
        """
        if self.min_quantity is None:
            return False
        return self.quantity < self.min_quantity

    def is_expired(self) -> bool:
        """Check if this inventory item has expired.

        Returns:
            True if expiration_date is in the past, False otherwise.
            If expiration_date is not set, returns False.
        """
        if self.expiration_date is None:
            return False
        return self.expiration_date < datetime.date.today()

    def expires_soon(self, threshold_days: int = EXPIRING_ITEMS_THRESHOLD_DAYS) -> bool:
        """Check if this inventory item will expire within the specified threshold.

        Args:
            threshold_days: Number of days to consider as "expiring soon"

        Returns:
            True if expiration_date is within threshold_days from today, False otherwise.
            If expiration_date is not set, returns False.
        """
        if self.expiration_date is None:
            return False

        threshold_date = datetime.date.today() + datetime.timedelta(days=threshold_days)
        return self.expiration_date <= threshold_date

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"InventoryItem(id={self.id!r}, kitchen_id={self.kitchen_id!r}, "
            f"food_item_id={self.food_item_id!r}, quantity={self.quantity!r}, "
            f"storage_location_id={self.storage_location_id!r})"
        )