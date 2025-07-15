"""Service for unit conversions - handles both food-specific and generic conversions."""

from sqlalchemy.orm import Session

from app.crud import core as crud_core
from app.crud import food as crud_food


class UnitConversionService:
    """Service for handling unit conversions - delegates to CRUD."""

    def __init__(self, db: Session):
        self.db = db

    def convert_to_base_unit(self, food_item_id: int, amount: float, from_unit_id: int) -> float:
        """Convert amount to base unit - delegates to CRUD.

        Args:
            food_item_id: ID of the food item
            amount: Amount to convert
            from_unit_id: Source unit ID

        Returns:
            Amount in base unit

        Raises:
            ValueError: If food item not found or conversion not possible
        """
        return crud_food.convert_to_base_unit(self.db, food_item_id, amount, from_unit_id)

    def get_available_units_for_food_item(self, food_item_id: int) -> list[tuple[int, str]]:
        """Get available units (both food-specific and generic) - delegates to CRUD.

        Args:
            food_item_id: ID of the food item

        Returns:
            List of (unit_id, unit_name) tuples
        """
        return crud_food.get_available_units_for_food_item(self.db, food_item_id)

    def get_compatible_units_for_base_unit(self, base_unit_id: int) -> list[tuple[int, str]]:
        """Get generic compatible units for a base unit.

        Args:
            base_unit_id: ID of the base unit

        Returns:
            List of (unit_id, unit_name) tuples
        """
        units = crud_core.get_compatible_units_for_base_unit(self.db, base_unit_id)
        return [(unit.id, unit.name) for unit in units]

    def get_all_available_units_for_food_item(self, food_item_id: int) -> list[tuple[int, str]]:
        """Get ALL available units (food-specific and generic) for a food item.

        Args:
            food_item_id: ID of the food item

        Returns:
            List of (unit_id, unit_name) tuples (deduplicated)
        """
        # Get food-specific units
        food_specific_units = self.get_available_units_for_food_item(food_item_id)

        # Get food item to find base unit
        food_item = crud_food.get_food_item_by_id(self.db, food_item_id)
        if not food_item or not food_item.base_unit_id:
            return food_specific_units

        # Get generic compatible units
        generic_units = self.get_compatible_units_for_base_unit(food_item.base_unit_id)

        # Combine and deduplicate
        all_units = {}
        for unit_id, unit_name in food_specific_units + generic_units:
            all_units[unit_id] = unit_name

        return list(all_units.items())
