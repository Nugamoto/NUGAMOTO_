"""SQLAlchemy ORM models for kitchen and user-kitchen relationships."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import KitchenRole
from app.db.base import Base
from app.models.user import User


class Kitchen(Base):
    """Represents a row in the ``kitchens`` table."""

    __tablename__ = "kitchens"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    user_kitchens: Mapped[list[UserKitchen]] = relationship(
        "UserKitchen", back_populates="kitchen", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return f"Kitchen(id={self.id!r}, name={self.name!r})"


class UserKitchen(Base):
    """Represents a row in the ``user_kitchens`` table.

    This is the association table between User and Kitchen with additional role data.
    """

    __tablename__ = "user_kitchens"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True
    )
    kitchen_id: Mapped[int] = mapped_column(
        ForeignKey("kitchens.id"), primary_key=True
    )
    role: Mapped[KitchenRole] = mapped_column(nullable=False, default=KitchenRole.MEMBER)

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    user: Mapped[User] = relationship("User", back_populates="user_kitchens")
    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="user_kitchens")

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"UserKitchen(user_id={self.user_id!r}, "
            f"kitchen_id={self.kitchen_id!r}, role={self.role!r})"
        )