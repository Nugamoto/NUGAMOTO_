"""SQLAlchemy ORM models for shopping system."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, String, Text, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PackageType, ShoppingListType
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
        ForeignKey("kitchens.id"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ShoppingListType] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
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
    """Global shopping product catalog.
    
    Represents a purchasable product that can be assigned to multiple shopping lists.
    """

    __tablename__ = "shopping_products"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    food_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("food_items.id"),
        nullable=False,
        index=True
    )
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    package_type: Mapped[PackageType] = mapped_column(nullable=False)
    estimated_price: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    food_item: Mapped[FoodItem] = relationship("FoodItem")
    assignments: Mapped[list[ShoppingProductAssignment]] = relationship(
        "ShoppingProductAssignment",
        back_populates="shopping_product",
        cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"ShoppingProduct(id={self.id!r}, food_item_id={self.food_item_id!r}, "
            f"quantity={self.quantity!r}, unit={self.unit!r}, "
            f"package_type={self.package_type!r})"
        )


class ShoppingProductAssignment(Base):
    """Assignment of a shopping product to a specific shopping list.
    
    This is the join table that connects shopping lists with products,
    allowing the same product to be on multiple lists with different contexts.
    """

    __tablename__ = "shopping_product_assignments"

    # ------------------------------------------------------------------ #
    # Columns (Composite Primary Key)                                    #
    # ------------------------------------------------------------------ #
    shopping_list_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_lists.id"),
        primary_key=True,
        index=True
    )
    shopping_product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_products.id"),
        primary_key=True,
        index=True
    )

    # ------------------------------------------------------------------ #
    # Additional Columns                                                  #
    # ------------------------------------------------------------------ #
    added_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )
    is_auto_added: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
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
