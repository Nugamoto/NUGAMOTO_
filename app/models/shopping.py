"""SQLAlchemy ORM models for shopping list functionality."""

from __future__ import annotations

from datetime import datetime, UTC
from enum import Enum

from sqlalchemy import DateTime, Float, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShoppingListType(str, Enum):
    """Enumeration of shopping list types."""

    SUPERMARKET = "supermarket"
    ONLINE = "online"
    FARMERS_MARKET = "farmers_market"
    CONVENIENCE_STORE = "convenience_store"
    SPECIALTY_STORE = "specialty_store"


class PackageType(str, Enum):
    """Enumeration of package types for shopping list items."""

    PACKAGE = "package"  # Packung
    LOOSE = "loose"  # Lose
    CAN = "can"  # Dose
    BOTTLE = "bottle"  # Flasche
    TUBE = "tube"  # Tube
    BAG = "bag"  # Tüte/Beutel
    BOX = "box"  # Karton/Box
    JAR = "jar"  # Glas
    POUCH = "pouch"  # Beutel
    TRAY = "tray"  # Schale


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
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    items: Mapped[list[ShoppingListItem]] = relationship(
        "ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"ShoppingList(id={self.id!r}, kitchen_id={self.kitchen_id!r}, "
            f"name={self.name!r}, type={self.type!r})"
        )


class ShoppingListItem(Base):
    """Represents a row in the ``shopping_list_items`` table.

    Items can be added manually by users or automatically by the AI system.
    Each item links to a food item and includes quantity, unit, and optional pricing.
    """

    __tablename__ = "shopping_list_items"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shopping_list_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shopping_lists.id"),
        nullable=False,
        index=True
    )
    food_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("food_items.id"),
        nullable=False,
        index=True
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    package_type: Mapped[PackageType | None] = mapped_column(default=None)
    estimated_price: Mapped[float | None] = mapped_column(Float, default=None)
    is_auto_added: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    added_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    shopping_list: Mapped[ShoppingList] = relationship(
        "ShoppingList", back_populates="items"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"ShoppingListItem(id={self.id!r}, shopping_list_id={self.shopping_list_id!r}, "
            f"food_item_id={self.food_item_id!r}, quantity={self.quantity!r})"
        )
