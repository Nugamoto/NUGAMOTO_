"""SQLAlchemy ORM models for core unit system."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UnitType
from app.db.base import Base

if TYPE_CHECKING:
    pass


class Unit(Base):
    """Represents a row in the ``units`` table.

    Units are used throughout the system for recipes, inventory, and shopping.
    Each unit has a type and a conversion factor to its base unit.
    """

    __tablename__ = "units"

    # ------------------------------------------------------------------ #
    # Columns                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Unit name (e.g., 'g', 'ml', 'piece', 'pack')"
    )
    type: Mapped[UnitType] = mapped_column(
        String(20),
        nullable=False,
        comment="Unit type: weight, volume, count, measure, or package"
    )
    to_base_factor: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Factor to convert to base unit (e.g., 1000 for kg → g)"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    conversions_from: Mapped[list[UnitConversion]] = relationship(
        "UnitConversion",
        foreign_keys="UnitConversion.from_unit_id",
        back_populates="from_unit"
    )
    conversions_to: Mapped[list[UnitConversion]] = relationship(
        "UnitConversion",
        foreign_keys="UnitConversion.to_unit_id",
        back_populates="to_unit"
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"Unit(id={self.id!r}, name={self.name!r}, "
            f"type={self.type!r}, to_base_factor={self.to_base_factor!r})"
        )


class UnitConversion(Base):
    """Represents a row in the ``unit_conversions`` table.

    Defines conversion factors between different units.
    Uses a composite primary key of from_unit_id and to_unit_id.
    """

    __tablename__ = "unit_conversions"

    # ------------------------------------------------------------------ #
    # Columns (Composite Primary Key)                                    #
    # ------------------------------------------------------------------ #
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
        comment="Target unit for conversion"
    )

    # ------------------------------------------------------------------ #
    # Conversion Data                                                     #
    # ------------------------------------------------------------------ #
    factor: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Conversion factor: value_in_from_unit * factor = value_in_to_unit"
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                       #
    # ------------------------------------------------------------------ #
    from_unit: Mapped[Unit] = relationship(
        "Unit",
        foreign_keys=[from_unit_id],
        back_populates="conversions_from"
    )
    to_unit: Mapped[Unit] = relationship(
        "Unit",
        foreign_keys=[to_unit_id],
        back_populates="conversions_to"
    )

    # ------------------------------------------------------------------ #
    # Table Constraints                                                   #
    # ------------------------------------------------------------------ #
    __table_args__ = (
        UniqueConstraint('from_unit_id', 'to_unit_id', name='uq_unit_conversion'),
    )

    # ------------------------------------------------------------------ #
    # Dunder                                                               #
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:  # noqa: D401 – we want a short repr
        return (
            f"UnitConversion(from_unit_id={self.from_unit_id!r}, "
            f"to_unit_id={self.to_unit_id!r}, factor={self.factor!r})"
        )
