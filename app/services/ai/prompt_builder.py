
"""Builder for individual prompt sections using templates."""

from sqlalchemy.orm import Session

from app.schemas.user import UserRead
from app.schemas.device import ApplianceWithDeviceType, KitchenToolWithDeviceType
from app.schemas.ai_service import PromptContext, RecipeGenerationRequest
from app.services.ai.prompt_templates import (
    USER_PROFILE_TEMPLATE,
    INVENTORY_TEMPLATE,
    EQUIPMENT_TEMPLATE,
    SECTION_HEADERS,
    COMMON_MESSAGES
)
from app.services.conversions.unit_conversion_service import UnitConversionService
from app.services.ai.inventory_prompt_service import InventoryPromptService


class PromptSectionBuilder:
    """Builder for individual prompt sections using templates."""

    def __init__(self, db: Session):
        self.db = db
        self.unit_conversion_service = UnitConversionService(db)
        self.inventory_prompt_service = InventoryPromptService(self.unit_conversion_service)

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

    def build_inventory_section(self, context: PromptContext) -> str:
        """Build inventory section using template."""
        if not context.inventory_items:
            return INVENTORY_TEMPLATE.build({})

        # Use the inventory service
        ingredient_lines = self.inventory_prompt_service.format_inventory_items(context.inventory_items)

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

    def build_priority_section(self, context: PromptContext) -> str:
        """Build priority ingredients section."""
        priority_lines = []

        if context.request.prioritize_expiring and context.expiring_items:
            priority_lines.append(SECTION_HEADERS['priority_ingredients'])
            expiring_lines = self.inventory_prompt_service.format_priority_ingredients(context.expiring_items)
            priority_lines.extend(expiring_lines)

        if context.low_stock_items:
            if priority_lines:
                priority_lines.append("")
            priority_lines.append(SECTION_HEADERS['low_stock_items'])
            low_stock_lines = self.inventory_prompt_service.format_low_stock_items(context.low_stock_items)
            priority_lines.extend(low_stock_lines)

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