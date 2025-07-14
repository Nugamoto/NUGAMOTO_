
"""Enhanced modular prompt builder for AI services."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Union

from sqlalchemy.orm import Session

from app.schemas.ai_service import RecipeGenerationRequest, PromptContext
from app.schemas.device import ApplianceWithDeviceType, KitchenToolWithDeviceType
from app.schemas.user import UserRead
from app.services.ai.prompt_templates import (
    RECIPE_GENERATION_TEMPLATE,
    INVENTORY_ANALYSIS_TEMPLATE,
    COOKING_SUGGESTIONS_TEMPLATE,
    SECTION_HEADERS,
    STATUS_INDICATORS,
    COMMON_MESSAGES,
    RECIPE_REQUIREMENTS,
    USER_PROFILE_TEMPLATE,
    INVENTORY_TEMPLATE,
    EQUIPMENT_TEMPLATE,
)

if TYPE_CHECKING:
    from app.schemas.inventory import InventoryItemRead
    from app.schemas.food import FoodItemRead, FoodItemWithConversions


class PromptSectionBuilder:
    """Builder for individual prompt sections using templates."""

    @staticmethod
    def build_user_section(user: UserRead) -> str:
        """Build user profile section using template."""
        user_data = {
            "name": user.name,
            "diet_type": user.diet_type or "Not specified",
            "allergies": user.allergies or "None",
            "preferences": user.preferences or "None"
        }

        return USER_PROFILE_TEMPLATE.build(user_data)

    @staticmethod
    def build_inventory_section(context: PromptContext) -> str:
        """Build inventory section using template."""
        if not context.inventory_items:
            return USER_PROFILE_TEMPLATE.build({})

        ingredient_lines = []
        sorted_items = sorted(
            context.inventory_items,
            key=lambda x: (not x.expires_soon, not x.is_low_stock, x.food_item.name)
        )

        for item in sorted_items:
            ingredient_lines.append(
                PromptSectionBuilder._format_ingredient_item(item)
            )

        category_summary = ""
        if context.available_categories:
            category_summary = f"{SECTION_HEADERS['available_categories']} {', '.join(context.available_categories.keys())}"

        inventory_data = {
            "ingredient_list": "\n".join(ingredient_lines),
            "category_summary": category_summary,
            "important_message": COMMON_MESSAGES['important_ids']
        }

        return INVENTORY_TEMPLATE.build(inventory_data)

    @staticmethod
    def _format_ingredient_item(item: InventoryItemRead) -> str:
        """Format individual inventory item."""
        food_item: Union[FoodItemRead, FoodItemWithConversions] = item.food_item
        base_unit = food_item.base_unit
        base_unit_name = base_unit.name if base_unit else 'units'
        quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"

        available_units = []

        if base_unit:
            available_units.append(f"{base_unit.name} (ID: {base_unit.id})")

        if hasattr(food_item, 'unit_conversions') and getattr(food_item, 'unit_conversions', None):
            conversions = getattr(food_item, 'unit_conversions')
            for conversion in conversions:
                if conversion.from_unit_id != base_unit.id:
                    available_units.append(f"{conversion.from_unit_name} (ID: {conversion.from_unit_id})")
                if conversion.to_unit_id != base_unit.id:
                    available_units.append(f"{conversion.to_unit_name} (ID: {conversion.to_unit_id})")

        if base_unit:
            try:
                from app.crud import core as crud_core
                from app.db.session import SessionLocal

                db = SessionLocal()
                try:
                    compatible_units = crud_core.get_compatible_units_for_base_unit(db, base_unit.id)
                    for unit in compatible_units:
                        if unit.id != base_unit.id:
                            available_units.append(f"{unit.name} (ID: {unit.id})")
                finally:
                    db.close()
            except Exception:
                pass

        available_units = sorted(list(set(available_units)))

        line = f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name}"

        if available_units:
            line += f" | Available Units: {', '.join(available_units)}"

        indicators = []
        if item.expires_soon:
            days_left = (item.expiration_date - datetime.date.today()).days if item.expiration_date else None
            indicators.append(STATUS_INDICATORS["expires_soon"].format(days=days_left))
        elif item.is_expired:
            indicators.append(STATUS_INDICATORS["expired"])

        if item.is_low_stock:
            indicators.append(STATUS_INDICATORS["low_stock"])

        if indicators:
            line += f" | {' | '.join(indicators)}"
        elif item.expiration_date:
            line += f" | Expires: {item.expiration_date.strftime('%Y-%m-%d')}"

        return line

    @staticmethod
    def build_equipment_section(
        appliances: list[ApplianceWithDeviceType],
        tools: list[KitchenToolWithDeviceType]
    ) -> str:
        """Build equipment section using template."""
        if not appliances and not tools:
            return EQUIPMENT_TEMPLATE.build({})

        appliances_section = ""
        if appliances:
            appliances_lines = ["Appliances:"]
            for appliance in appliances:
                line = f"- {appliance.display_name}"
                if appliance.capacity_liters:
                    line += f" ({appliance.capacity_liters}L capacity)"
                if hasattr(appliance, 'device_type_name'):
                    line += f" | Type: {appliance.device_type_name}"
                appliances_lines.append(line)
            appliances_section = "\n".join(appliances_lines)

        tools_section = ""
        if tools:
            tools_lines = ["Tools:"]
            for tool in tools:
                line = f"- {tool.name}"
                if tool.size_or_detail:
                    line += f" ({tool.size_or_detail})"
                if tool.quantity and tool.quantity > 1:
                    line += f" (x{tool.quantity})"
                if hasattr(tool, 'device_type_name'):
                    line += f" | Type: {tool.device_type_name}"
                tools_lines.append(line)
            tools_section = "\n".join(tools_lines)

        equipment_data = {
            "appliances_section": appliances_section,
            "tools_section": tools_section
        }

        return EQUIPMENT_TEMPLATE.build(equipment_data)

    @staticmethod
    def build_priority_section(context: PromptContext) -> str:
        """Build priority ingredients section."""
        priority_lines = []

        if context.request.prioritize_expiring and context.expiring_items:
            priority_lines.append(SECTION_HEADERS['priority_ingredients'])
            for item in context.expiring_items:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"
                days_left = (item.expiration_date - datetime.date.today()).days if item.expiration_date else None
                priority_lines.append(
                    f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name} - expires in {days_left} days"
                )

        if context.low_stock_items:
            if priority_lines:
                priority_lines.append("")
            priority_lines.append(SECTION_HEADERS['low_stock_items'])
            for item in context.low_stock_items:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"
                priority_lines.append(
                    f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name}"
                )

        if context.request.required_appliances:
            if priority_lines:
                priority_lines.append("")
            priority_lines.append(f"REQUIRED APPLIANCES: {', '.join(context.request.required_appliances)}")

        if context.request.avoid_appliances:
            if priority_lines:
                priority_lines.append("")
            priority_lines.append(f"AVOID APPLIANCES: {', '.join(context.request.avoid_appliances)}")

        return "\n".join(priority_lines) if priority_lines else COMMON_MESSAGES['no_priorities']

    @staticmethod
    def build_request_section(request: RecipeGenerationRequest) -> str:
        """Build request context section."""
        lines = [SECTION_HEADERS['recipe_request']]

        request_fields = [
            ("cuisine_type", "Cuisine"),
            ("meal_type", "Meal Type"),
            ("difficulty_level", "Difficulty"),
            ("max_prep_time", "Max Prep Time", "minutes"),
            ("max_cook_time", "Max Cook Time", "minutes"),
            ("servings", "Servings"),
        ]

        for field_data in request_fields:
            field_name = field_data[0]
            display_name = field_data[1]
            suffix = field_data[2] if len(field_data) > 2 else ""

            value = getattr(request, field_name)
            if value:
                line = f"- {display_name}: {value}"
                if suffix:
                    line += f" {suffix}"
                lines.append(line)

        if request.dietary_restrictions:
            lines.append(f"- Dietary Restrictions: {', '.join(request.dietary_restrictions)}")

        if request.exclude_ingredients:
            lines.append(f"- Exclude: {', '.join(request.exclude_ingredients)}")

        if request.special_requests:
            lines.append(f"- Special Requests: {request.special_requests}")

        preferences = []
        if request.prioritize_expiring:
            preferences.append("prioritize expiring ingredients")
        if request.prefer_available_ingredients:
            preferences.append("prefer available ingredients")

        if preferences:
            lines.append(f"- Preferences: {', '.join(preferences)}")

        return "\n".join(lines)


class PromptBuilder:
    """Enhanced modular prompt builder using templates and section builders."""

    def __init__(self, db: Session):
        """Initialize prompt builder with database session."""
        self.db = db
        self.section_builder = PromptSectionBuilder()

    def build_recipe_prompt(
        self,
        request: RecipeGenerationRequest,
        user_id: int,
        kitchen_id: int
    ) -> tuple[str, str]:
        """Build recipe generation prompt using templates."""
        context = PromptContext.build_from_ids(
            db=self.db,
            user_id=user_id,
            kitchen_id=kitchen_id,
            request=request
        )

        user_context = self.section_builder.build_user_section(context.user)
        inventory_context = self.section_builder.build_inventory_section(context)
        equipment_context = self.section_builder.build_equipment_section(
            context.appliances, context.tools
        )
        priority_context = self.section_builder.build_priority_section(context)
        request_context = self.section_builder.build_request_section(context.request)

        requirements = f"{SECTION_HEADERS['requirements']}\n" + "\n".join(
            f"- {req}" for req in RECIPE_REQUIREMENTS
        )

        return RECIPE_GENERATION_TEMPLATE.build_complete_prompt(
            user_context=user_context,
            inventory_context=inventory_context,
            equipment_context=equipment_context,
            priority_context=priority_context,
            request_context=request_context,
            requirements=requirements,
            closing_message=COMMON_MESSAGES['json_format']
        )

    def build_inventory_analysis_prompt(self, kitchen_id: int) -> tuple[str, str]:
        """Build inventory analysis prompt using templates."""
        analysis_request = RecipeGenerationRequest(
            special_requests="Analyze inventory for insights and recommendations"
        )

        context = PromptContext.build_from_ids(
            db=self.db,
            user_id=1,
            kitchen_id=kitchen_id,
            request=analysis_request
        )

        analysis_sections = []

        if context.expiring_items:
            analysis_sections.append(f"{SECTION_HEADERS['expiring_soon']}")
            for item in context.expiring_items:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                days_left = (item.expiration_date - datetime.date.today()).days if item.expiration_date else None
                analysis_sections.append(
                    f"- {food_item.name}: {item.quantity} {base_unit_name} (expires in {days_left} days)"
                )

        if context.low_stock_items:
            analysis_sections.append(f"\n{SECTION_HEADERS['low_stock_items']}")
            for item in context.low_stock_items:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                analysis_sections.append(
                    f"- {food_item.name}: {item.quantity} {base_unit_name} (below minimum)"
                )

        good_items = [
            item for item in context.inventory_items
            if not item.expires_soon and not item.is_low_stock and not item.is_expired
        ]

        if good_items:
            analysis_sections.append(f"\n{SECTION_HEADERS['good_condition']}")
            for item in good_items[:10]:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                analysis_sections.append(f"- {food_item.name}: {item.quantity} {base_unit_name}")

        if context.available_categories:
            analysis_sections.append(
                f"\n{SECTION_HEADERS['available_categories']} {', '.join(context.available_categories.keys())}"
            )

        return INVENTORY_ANALYSIS_TEMPLATE.build_complete_prompt(
            analysis_sections="\n".join(analysis_sections)
        )

    def build_cooking_suggestions_prompt(
        self,
        user_id: int,
        kitchen_id: int
    ) -> tuple[str, str]:
        """Build cooking suggestions prompt using templates."""
        suggestion_request = RecipeGenerationRequest(
            special_requests="Provide 3-5 quick meal suggestions based on available ingredients"
        )

        context = PromptContext.build_from_ids(
            db=self.db,
            user_id=user_id,
            kitchen_id=kitchen_id,
            request=suggestion_request
        )

        user_context = self.section_builder.build_user_section(context.user)
        inventory_context = self.section_builder.build_inventory_section(context)
        equipment_context = self.section_builder.build_equipment_section(
            context.appliances, context.tools
        )

        return COOKING_SUGGESTIONS_TEMPLATE.build_complete_prompt(
            user_context=user_context,
            inventory_context=inventory_context,
            equipment_context=equipment_context
        )