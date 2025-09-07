"""Service for building inventory-related prompt sections."""

import datetime
from typing import Union, TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from backend.services.conversions.unit_conversion_service import UnitConversionService

if TYPE_CHECKING:
    from backend.schemas.food import FoodItemRead, FoodItemWithConversions
    from backend.schemas.inventory import InventoryItemRead


class InventoryPromptService:
    """Service for building inventory sections in AI prompts."""


    def __init__(self, unit_conversion_service: UnitConversionService):
        self.unit_conversion_service = unit_conversion_service


    def format_inventory_items(self, items: list["InventoryItemRead"]) -> list[str]:
        """Format inventory items for prompt display.

        Args:
            items: List of inventory items to format

        Returns:
            List of formatted item strings
        """
        if not items:
            return []

        # Sort items by priority (expiring, low stock, then alphabetically)
        sorted_items = sorted(
            items,
            key=lambda x: (not x.expires_soon, not x.is_low_stock, x.food_item.name)
        )

        formatted_items = []
        for item in sorted_items:
            formatted_item = self._format_single_item(item)
            formatted_items.append(formatted_item)

        return formatted_items


    def _format_single_item(self, item: "InventoryItemRead") -> str:
        """Format a single inventory item.

        Args:
            item: Inventory item to format

        Returns:
            Formatted item string
        """
        from backend.schemas.food import FoodItemRead, FoodItemWithConversions

        food_item: Union[FoodItemRead, FoodItemWithConversions] = item.food_item

        # Basic item info
        base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
        quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"

        line = f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name}"

        # Add available units
        available_units = self._get_available_units_display(food_item)
        if available_units:
            line += f" | Available Units: {', '.join(available_units)}"

        # Add status indicators
        status_indicators = self._get_status_indicators(item)
        if status_indicators:
            line += f" | {' | '.join(status_indicators)}"
        elif item.expiration_date:
            line += f" | Expires: {item.expiration_date.strftime('%Y-%m-%d')}"

        return line


    def _get_available_units_display(self, food_item: Union["FoodItemRead", "FoodItemWithConversions"]) -> list[str]:
        """Get available units display for a food item with COMPLETE original logic.

        Args:
            food_item: Food item to get units for

        Returns:
            List of formatted unit strings
        """
        available_units = []
        base_unit = food_item.base_unit

        try:
            # First, try to get units from the unit conversion service
            service_units = self.unit_conversion_service.get_all_available_units_for_food_item(food_item.id)

            # Format as "unit_name (ID: unit_id)"
            for unit_id, unit_name in service_units:
                available_units.append(f"{unit_name} (ID: {unit_id})")

        except (ValueError, SQLAlchemyError):
            # Fallback to original complex logic if service fails

            # Add base unit first
            if base_unit:
                available_units.append(f"{base_unit.name} (ID: {base_unit.id})")

            # Add food-specific conversions (from original logic)
            if hasattr(food_item, 'unit_conversions') and getattr(food_item, 'unit_conversions', None):
                conversions = getattr(food_item, 'unit_conversions')
                for conversion in conversions:
                    if conversion.from_unit_id != base_unit.id:
                        available_units.append(f"{conversion.from_unit_name} (ID: {conversion.from_unit_id})")
                    if conversion.to_unit_id != base_unit.id:
                        available_units.append(f"{conversion.to_unit_name} (ID: {conversion.to_unit_id})")

            # Add generic compatible units (from original logic)
            if base_unit:
                try:
                    from backend.crud import core as crud_core
                    from backend.db.session import SessionLocal

                    db = SessionLocal()
                    try:
                        compatible_units = crud_core.get_compatible_units_for_base_unit(db, base_unit.id)
                        for unit in compatible_units:
                            if unit.id != base_unit.id:
                                available_units.append(f"{unit.name} (ID: {unit.id})")
                    finally:
                        db.close()
                except (ImportError, SQLAlchemyError):
                    # Final fallback to base unit only
                    if base_unit and not available_units:
                        available_units.append(f"{base_unit.name} (ID: {base_unit.id})")

        # Remove duplicates and sort
        available_units = sorted(list(set(available_units)))
        return available_units


    @staticmethod
    def _get_status_indicators(item: "InventoryItemRead") -> list[str]:
        """Get status indicators for an inventory item.

        Args:
            item: Inventory item to check

        Returns:
            List of status indicator strings
        """
        from backend.services.ai.prompt_templates import STATUS_INDICATORS

        indicators = []

        if item.expires_soon:
            days_left = (item.expiration_date - datetime.date.today()).days if item.expiration_date else None
            if days_left is not None:
                indicators.append(STATUS_INDICATORS["expires_soon"].format(days=days_left))
            else:
                indicators.append("⚠️ EXPIRES SOON")
        elif item.is_expired:
            indicators.append(STATUS_INDICATORS["expired"])

        if item.is_low_stock:
            indicators.append(STATUS_INDICATORS["low_stock"])

        return indicators


    @staticmethod
    def format_priority_ingredients(expiring_items: list["InventoryItemRead"]) -> list[str]:
        """Format priority ingredients (expiring items).

        Args:
            expiring_items: List of expiring inventory items

        Returns:
            List of formatted priority ingredient strings
        """
        if not expiring_items:
            return []

        priority_lines = []
        for item in expiring_items:
            food_item = item.food_item
            base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
            quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"

            days_left = None
            if item.expiration_date:
                days_left = (item.expiration_date - datetime.date.today()).days

            line = f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name}"
            if days_left is not None:
                line += f" - expires in {days_left} days"

            priority_lines.append(line)

        return priority_lines


    @staticmethod
    def format_low_stock_items(low_stock_items: list["InventoryItemRead"]) -> list[str]:
        """Format low stock items.

        Args:
            low_stock_items: List of low-stock inventory items

        Returns:
            List of formatted low stock item strings
        """
        if not low_stock_items:
            return []

        low_stock_lines = []
        for item in low_stock_items:
            food_item = item.food_item
            base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
            quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"

            line = f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name}"
            low_stock_lines.append(line)

        return low_stock_lines