"""SQLAlchemy ORM models for food system."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.core import Unit
    from app.models.inventory import InventoryItem


class FoodItem(Base):
    """Represents a row in the ``food_items`` table.

    Food items are global entities that can be used across all kitchens.
    They represent basic food categories like "Tomato", "Rice", etc.

    Each food item has a base_unit_id that defines the standard
    measurement unit for storing quantities (e.g., grams, ml, pieces).
    """

    __tablename__ = "food_items"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Name of the food item (e.g., 'Tomato', 'Rice')"
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Food category (e.g., 'Vegetables', 'Grains')"
    )
    base_unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id"),
        nullable=False,
        index=True,
        comment="Reference to the base unit for this food item"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    last_updated: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    base_unit: Mapped[Unit] = relationship(
        "Unit",
        foreign_keys=[base_unit_id]
    )
    inventory_items: Mapped[list[InventoryItem]] = relationship(
        "InventoryItem",
        back_populates="food_item"
    )
    unit_conversions: Mapped[list[FoodItemUnitConversion]] = relationship(
        "FoodItemUnitConversion",
        back_populates="food_item",
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"FoodItem(id={self.id!r}, name={self.name!r}, "
            f"category={self.category!r}, base_unit_id={self.base_unit_id!r})"
        )


class FoodItemUnitConversion(Base):
    """Represents a row in the ``food_item_unit_conversions`` table.

    Defines specific conversion factors for individual food items.
    For example: "1 cup oats = 80 g" where oats is the food item.
    Uses composite primary key of food_item_id, from_unit_id, and to_unit_id.
    """

    __tablename__ = "food_item_unit_conversions"

    # ------------------------------------------------------------------ #
    # Columns (Composite Primary Key)                                    #
    # ------------------------------------------------------------------ #
    food_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("food_items.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Food item this conversion applies to"
    )
    from_unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("units.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Source unit for conversion"
    )
    to_unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("units.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Target unit for conversion (usually base_unit)"
    )

    # ------------------------------------------------------------------ #
    # Conversion Data                                                     #
    # ------------------------------------------------------------------ #
    factor: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Conversion factor: amount_in_from_unit * factor = amount_in_to_unit"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    food_item: Mapped[FoodItem] = relationship(
        "FoodItem",
        back_populates="unit_conversions"
    )
    from_unit: Mapped[Unit] = relationship(
        "Unit",
        foreign_keys=[from_unit_id]
    )
    to_unit: Mapped[Unit] = relationship(
        "Unit",
        foreign_keys=[to_unit_id]
    )

    # ------------------------------------------------------------------ #
    # Table Constraints                                                   #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint(
            'food_item_id', 'from_unit_id', 'to_unit_id',
            name='uq_food_item_unit_conversion'
        ),
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"FoodItemUnitConversion(food_item_id={self.food_item_id!r}, "
            f"from_unit_id={self.from_unit_id!r}, to_unit_id={self.to_unit_id!r}, "
            f"factor={self.factor!r})"
        )