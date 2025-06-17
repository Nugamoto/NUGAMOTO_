"""Core enums for the NUGAMOTO application."""

from __future__ import annotations

from enum import Enum


class UnitType(str, Enum):
    """Enumeration of unit types."""

    WEIGHT = "weight"
    VOLUME = "volume"
    COUNT = "count"
    MEASURE = "measure"
    PACKAGE = "package"

class KitchenRole(str, Enum):
    """Valid roles for users in kitchens."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


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


class OutputType(str, Enum):
    """Enumeration of AI output types."""

    RECIPE = "recipe"
    NUTRITION_TIP = "nutrition_tip"
    SHOPPING_LIST = "shopping_list"
    COACHING_MESSAGE = "coaching_message"
    SHOPPING_SUGGESTION = "shopping_suggestion"
    GENERAL = "general"  # For anything that doesn't fit other categories


class OutputFormat(str, Enum):
    """Enumeration of AI output formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"


class AIOutputTargetType(str, Enum):
    """Enumeration of AI output target types for polymorphic associations."""

    RECIPE = "Recipe"
    SHOPPING_LIST = "ShoppingList"
    INVENTORY_ITEM = "InventoryItem"
    USER = "User"
    KITCHEN = "Kitchen"
    FOOD_ITEM = "FoodItem"
    PRODUCT = "Product"
