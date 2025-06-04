"""Core enums for the NUGAMOTO application."""

from __future__ import annotations

from enum import Enum


class PackageType(str, Enum):
    """Package types for shopping products."""

    TETRA_PAK = "tetra_pak"
    DOSE = "dose"
    LOSE = "lose"
    BOTTLE = "bottle"
    BAG = "bag"
    BOX = "box"
    TUBE = "tube"
    JAR = "jar"
    PACKAGE = "package"
    BULK = "bulk"


class ShoppingListType(str, Enum):
    """Types of shopping lists."""

    SUPERMARKET = "supermarket"
    ONLINE = "online"
    FARMERS_MARKET = "farmers_market"
    CONVENIENCE_STORE = "convenience_store"
    SPECIALTY_STORE = "specialty_store"
    WHOLESALE = "wholesale"
