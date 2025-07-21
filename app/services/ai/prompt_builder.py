"""Builder for individual prompt sections using templates."""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.schemas.ai_service import PromptContext, RecipeGenerationRequest
    from app.schemas.device import ApplianceWithDeviceType, KitchenToolWithDeviceType
    from app.schemas.user import UserRead
from app.services.ai.inventory_prompt_service import InventoryPromptService
from app.services.ai.prompt_templates import (
    USER_PROFILE_TEMPLATE,
    INVENTORY_TEMPLATE,
    EQUIPMENT_TEMPLATE,
    SECTION_HEADERS,
    COMMON_MESSAGES,
    NUGAMOTO_RECIPE_SYSTEM_PROMPT,
    NUGAMOTO_INVENTORY_SYSTEM_PROMPT,
    RECIPE_REQUIREMENTS
)
from app.services.conversions.unit_conversion_service import UnitConversionService


class PromptSectionBuilder:
    """Builder for individual prompt sections using templates."""


    def __init__(self, db: Session):
        self.db = db
        self.unit_conversion_service = UnitConversionService(db)
        self.inventory_prompt_service = InventoryPromptService(self.unit_conversion_service)


    @staticmethod
    def build_user_section(user: "UserRead") -> str:
        """Build user profile section using template."""
        user_data = {
            "name": user.name,
            "diet_type": user.diet_type or "Not specified",
            "allergies": user.allergies or "None",
            "preferences": user.preferences or "None"
        }

        return USER_PROFILE_TEMPLATE.build(user_data)


    def build_inventory_section(self, context: "PromptContext") -> str:
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
            appliances: list["ApplianceWithDeviceType"],
            tools: list["KitchenToolWithDeviceType"]
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


    def build_priority_section(self, context: "PromptContext") -> str:
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
    def build_request_section(request: "RecipeGenerationRequest") -> str:
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
    """Main prompt builder that orchestrates section building."""


    def __init__(self, db: Session):
        """Initialize prompt builder with database session."""
        self.db = db
        self.section_builder = PromptSectionBuilder(db)


    def build_recipe_prompt(
            self,
            request: "RecipeGenerationRequest",
            user_id: int,
            kitchen_id: int
    ) -> tuple[str, str]:
        """Build recipe generation prompt using templates.

        Args:
            request: Recipe generation request
            user_id: User ID
            kitchen_id: Kitchen ID

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        from app.schemas.ai_service import PromptContext

        # Build context from database
        context = PromptContext.build_from_ids(
            db=self.db,
            user_id=user_id,
            kitchen_id=kitchen_id,
            request=request
        )

        # Build individual sections
        user_context = self.section_builder.build_user_section(context.user)
        inventory_context = self.section_builder.build_inventory_section(context)
        equipment_context = self.section_builder.build_equipment_section(
            context.appliances, context.tools
        )
        priority_context = self.section_builder.build_priority_section(context)
        request_context = self.section_builder.build_request_section(context.request)

        # Build requirements section
        requirements = f"{SECTION_HEADERS['requirements']}\n" + "\n".join(
            f"- {req}" for req in RECIPE_REQUIREMENTS
        )

        # Combine all sections into user prompt
        user_prompt = f"""Please generate a recipe based on the following information:

{user_context}

{inventory_context}

{equipment_context}

{priority_context}

{request_context}

{requirements}

{COMMON_MESSAGES['json_format']}"""

        return NUGAMOTO_RECIPE_SYSTEM_PROMPT, user_prompt


    def build_inventory_analysis_prompt(self, kitchen_id: int) -> tuple[str, str]:
        """Build inventory analysis prompt using templates.

        Args:
            kitchen_id: Kitchen ID

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        from app.schemas.ai_service import RecipeGenerationRequest, PromptContext

        # Create basic request for inventory analysis
        analysis_request = RecipeGenerationRequest(
            special_requests="Analyze inventory for insights and recommendations"
        )

        # Build context
        context = PromptContext.build_from_ids(
            db=self.db,
            user_id=1,  # Default user for analysis
            kitchen_id=kitchen_id,
            request=analysis_request
        )

        # Build analysis sections
        analysis_sections = []

        # Expiring items
        if context.expiring_items:
            analysis_sections.append(f"{SECTION_HEADERS['expiring_soon']}")
            expiring_lines = self.section_builder.inventory_prompt_service.format_priority_ingredients(
                context.expiring_items
            )
            analysis_sections.extend(expiring_lines)

        # Low-stock items
        if context.low_stock_items:
            analysis_sections.append(f"\n{SECTION_HEADERS['low_stock_items']}")
            low_stock_lines = self.section_builder.inventory_prompt_service.format_low_stock_items(
                context.low_stock_items
            )
            analysis_sections.extend(low_stock_lines)

        # Good condition items (sample)
        good_items = [
            item for item in context.inventory_items
            if not item.expires_soon and not item.is_low_stock and not item.is_expired
        ]
        if good_items:
            analysis_sections.append(f"\n{SECTION_HEADERS['good_condition']}")
            for item in good_items[:10]:  # Show first 10
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"
                analysis_sections.append(f"- {food_item.name}: {quantity_str} {base_unit_name}")

        # Available categories
        if context.available_categories:
            analysis_sections.append(
                f"\n{SECTION_HEADERS['available_categories']} {', '.join(context.available_categories.keys())}"
            )

        user_prompt = f"""Please analyze this kitchen inventory:

{chr(10).join(analysis_sections)}

Provide a comprehensive analysis with recommendations for optimal ingredient usage and waste reduction."""

        return NUGAMOTO_INVENTORY_SYSTEM_PROMPT, user_prompt