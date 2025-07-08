
"""SQLAlchemy models for kitchen devices and tools."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.kitchen import Kitchen


class DeviceType(Base):
    """Defines types of kitchen devices and tools with default characteristics."""

    __tablename__ = "device_types"

    # ------------------------------------------------------------------ #
    # Columns                                                            #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Name of the device type (e.g., 'Oven', 'Chef's Knife')"
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Category classification (e.g., 'appliance', 'tool', 'cookware')"
    )
    default_smart: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether devices of this type are typically smart by default"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp when device type was created"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp of last device type update"
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                      #
    # ------------------------------------------------------------------ #
    appliances: Mapped[list[Appliance]] = relationship(
        "Appliance", back_populates="device_type", cascade="all, delete-orphan"
    )
    kitchen_tools: Mapped[list[KitchenTool]] = relationship(
        "KitchenTool", back_populates="device_type", cascade="all, delete-orphan"
    )

    # ------------------------------------------------------------------ #
    # Properties                                                         #
    # ------------------------------------------------------------------ #
    @property
    def is_appliance_category(self) -> bool:
        """Check if this device type is categorized as an appliance."""
        return self.category.lower() == "appliance"

    @property
    def total_instances(self) -> int:
        """Get total number of instances (appliances plus tools) of this device type."""
        return len(self.appliances) + len(self.kitchen_tools)

    def __repr__(self) -> str:
        return f"DeviceType(id={self.id!r}, name={self.name!r}, category={self.category!r})"


class Appliance(Base):
    """Represents kitchen appliances with technical specifications."""

    __tablename__ = "appliances"

    # ------------------------------------------------------------------ #
    # Columns                                                            #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kitchen_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("kitchens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the kitchen this appliance belongs to"
    )
    device_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("device_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to the device type"
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Custom name for this appliance instance"
    )
    brand: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Manufacturer brand"
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Model number or name"
    )
    smart: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this appliance has smart/IoT capabilities"
    )
    capacity_liters: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Storage or working capacity in liters"
    )
    power_watts: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Power consumption in watts"
    )
    power_kw: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Power consumption in kilowatts"
    )
    year_purchased: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Year when the appliance was purchased"
    )
    available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the appliance is currently available for use"
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes about the appliance"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp when appliance was added"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp of last appliance update"
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                      #
    # ------------------------------------------------------------------ #
    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="appliances")
    device_type: Mapped[DeviceType] = relationship("DeviceType", back_populates="appliances")

    # ------------------------------------------------------------------ #
    # Properties                                                         #
    # ------------------------------------------------------------------ #
    @property
    def display_name(self) -> str:
        """Get a user-friendly display name combining brand, model, and name."""
        parts = []
        if self.brand:
            parts.append(self.brand)
        if self.model:
            parts.append(self.model)
        if parts:
            return f"{' '.join(parts)} ({self.name})"
        return self.name

    @property
    def age_years(self) -> int | None:
        """Calculate age in years if purchase year is available."""
        if self.year_purchased:
            current_year = datetime.datetime.now(datetime.timezone.utc).year
            return current_year - self.year_purchased
        return None

    @property
    def specifications(self) -> dict[str, str | float | None]:
        """Get technical specifications as a dictionary."""
        return {
            "capacity_liters": self.capacity_liters,
            "power_watts": self.power_watts,
            "power_kw": self.power_kw,
            "year_purchased": self.year_purchased,
            "smart_enabled": self.smart,
        }

    def __repr__(self) -> str:
        return f"Appliance(id={self.id!r}, name={self.name!r}, brand={self.brand!r})"


class KitchenTool(Base):
    """Represents kitchen tools with material and quantity specifications."""

    __tablename__ = "kitchen_tools"

    # ------------------------------------------------------------------ #
    # Columns                                                            #
    # ------------------------------------------------------------------ #
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    kitchen_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("kitchens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the kitchen this tool belongs to"
    )
    device_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("device_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to the device type"
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Name of this kitchen tool"
    )
    size_or_detail: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Size specification or descriptive detail"
    )
    material: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary material"
    )
    quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of identical items"
    )
    available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the tool is currently available for use"
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes about the tool"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp when tool was added"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        comment="Timestamp of last tool update"
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                      #
    # ------------------------------------------------------------------ #
    kitchen: Mapped[Kitchen] = relationship("Kitchen", back_populates="kitchen_tools")
    device_type: Mapped[DeviceType] = relationship("DeviceType", back_populates="kitchen_tools")

    # ------------------------------------------------------------------ #
    # Properties                                                         #
    # ------------------------------------------------------------------ #
    @property
    def full_description(self) -> str:
        """Get a comprehensive description of the tool."""
        parts = [self.name]

        if self.size_or_detail:
            parts.append(f"({self.size_or_detail})")

        if self.material:
            parts.append(f"- {self.material}")

        if self.quantity and self.quantity > 1:
            parts.append(f"x{self.quantity}")

        return " ".join(parts)

    @property
    def is_set(self) -> bool:
        """Check if this tool represents multiple items (quantity > 1)."""
        return self.quantity is not None and self.quantity > 1

    def __repr__(self) -> str:
        return f"KitchenTool(id={self.id!r}, name={self.name!r}, material={self.material!r})"