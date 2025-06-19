"""SQLAlchemy ORM models for shopping system v2.0."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, String, Text, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import ShoppingListType
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.kitchen import Kitchen
    from app.models.inventory import FoodItem
    from app.models.user import User


class ShoppingList(Base):
    """Represents a row in the ``shopping_lists`` table.

    Shopping lists belong to kitchens and can be categorized by type
    (supermarket, online, farmers market, etc.).
    """

    __tablename__ = "shopping_lists"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kitchen_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("kitchens.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ShoppingListType] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="shopping_lists")
    product_assignments: Mapped[list[ShoppingProductAssignment]] = relationship(
        "ShoppingProductAssignment",
        back_populates="shopping_list",
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"ShoppingList(id={self.id!r}, kitchen_id={self.kitchen_id!r}, "
            f"name={self.name!r}, type={self.type!r})"
        )


class ShoppingProduct(Base):
    """Global shopping product catalog (v2.0).
    
    Represents a purchasable product that can be assigned to multiple shopping lists.
    Each product defines a specific package with its unit, quantity, and base unit conversion.
    """

    __tablename__ = "shopping_products"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    food_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("food_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the base food item"
    )
    package_unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("units.id"),
        nullable=False,
        index=True,
        comment="Unit used for the package (e.g., 'pack', 'bottle', 'kg')"
    )
    package_quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Quantity per package in package_unit (e.g., 500 for '500g pack')"
    )
    quantity_in_base_unit: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Equivalent quantity in food item's base unit for inventory calculations"
    )
    package_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Descriptive package type (e.g., '500 g pack', '1 kg bag')"
    )
    estimated_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Estimated price for this package"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    food_item: Mapped[FoodItem] = relationship("FoodItem")
    # package_unit: Mapped[Unit] = relationship("Unit", foreign_keys=[package_unit_id])
    assignments: Mapped[list[ShoppingProductAssignment]] = relationship(
        "ShoppingProductAssignment",
        back_populates="shopping_product",
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Properties                                                          #
    # ------------------------------------------------------------------ #
    @property
    def unit_price(self) -> float | None:
        """Calculate price per base unit if price is available.
        
        Returns:
            Price per base unit (e.g., price per gram) or None if no price set.
        """
        if self.estimated_price is None or self.quantity_in_base_unit <= 0:
            return None
        return self.estimated_price / self.quantity_in_base_unit

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"ShoppingProduct(id={self.id!r}, food_item_id={self.food_item_id!r}, "
            f"package_quantity={self.package_quantity!r}, "
            f"package_type={self.package_type!r})"
        )


class ShoppingProductAssignment(Base):
    """Assignment of a shopping product to a specific shopping list (v2.0).
    
    This is the join table that connects shopping lists with products,
    allowing the same product to be on multiple lists with different contexts.
    Uses composite primary key for optimal performance.
    """

    __tablename__ = "shopping_product_assignments"

    # ------------------------------------------------------------------ #
    # Columns (Composite Primary Key)                                    #
    # ------------------------------------------------------------------ #
    shopping_list_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_lists.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    shopping_product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_products.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )

    # ------------------------------------------------------------------ #
    # Additional Columns                                                  #
    # ------------------------------------------------------------------ #
    added_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who added this item (NULL for system-generated)"
    )
    is_auto_added: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if added automatically by AI/system"
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User note about this specific assignment"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    shopping_list: Mapped[ShoppingList] = relationship(
        "ShoppingList", back_populates="product_assignments"
    )
    shopping_product: Mapped[ShoppingProduct] = relationship(
        "ShoppingProduct", back_populates="assignments"
    )
    added_by_user: Mapped[User | None] = relationship("User")

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"ShoppingProductAssignment("
            f"list_id={self.shopping_list_id!r}, "
            f"product_id={self.shopping_product_id!r}, "
            f"auto_added={self.is_auto_added!r})"
        )