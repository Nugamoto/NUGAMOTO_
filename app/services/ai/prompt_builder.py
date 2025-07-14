"""Dynamic prompt builder for AI services."""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.schemas.ai_service import RecipeGenerationRequest, PromptContext
from app.schemas.device import ApplianceWithDeviceType, KitchenToolWithDeviceType
from app.schemas.user import UserRead


class PromptBuilder:
    """Builder for dynamic AI prompts based on user data and kitchen state."""

    def __init__(self, db: Session):
        """Initialize prompt builder with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def build_recipe_prompt(
            self,
            request: RecipeGenerationRequest,
            user_id: int,
            kitchen_id: int
    ) -> tuple[str, str]:
        """Build system and user prompts for recipe generation.

        Args:
            request: Recipe generation request with preferences.
            user_id: ID of the requesting user.
            kitchen_id: ID of the kitchen.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        # Use structured context instead of individual CRUD calls
        context = PromptContext.build_from_ids(
            db=self.db,
            user_id=user_id,
            kitchen_id=kitchen_id,
            request=request
        )

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt_from_context(context)

        return system_prompt, user_prompt

    @staticmethod
    def _build_system_prompt() -> str:
        """Build the system prompt for recipe generation."""
        return """You are NUGAMOTO, an expert culinary AI assistant specializing in smart kitchen management.

Your expertise includes:
- Creating recipes based on available ingredients and kitchen equipment
- Accommodating dietary preferences and restrictions
- Suggesting cooking techniques optimized for available appliances
- Providing nutritional insights and meal planning advice
- Minimizing food waste through smart ingredient usage

Always respond with practical, achievable recipes that consider:
- User's dietary preferences and restrictions
- Available ingredients and their quantities
- Kitchen equipment capabilities
- Cooking skill level and time constraints
- Food safety and proper cooking techniques

CRITICAL: When using ingredients, always include the exact food_item_id from the inventory list provided."""

    @staticmethod
    def _build_user_prompt_from_context(context: PromptContext) -> str:
        """Build user prompt from structured context."""

        # Build sections using context
        user_context = PromptBuilder._build_user_context(context.user)
        inventory_context = PromptBuilder._build_inventory_context_enhanced(context)
        equipment_context = PromptBuilder._build_equipment_context_typed(context.appliances, context.tools)
        priority_context = PromptBuilder._build_priority_context(context)
        request_context = PromptBuilder._build_request_context(context.request)

        prompt = f"""Please generate a recipe based on the following information:

{user_context}

{inventory_context}

{equipment_context}

{priority_context}

{request_context}

Requirements:
- Use available ingredients efficiently
- Consider dietary preferences and restrictions
- PRIORITIZE expiring ingredients when possible
- Suggest appropriate cooking methods for available equipment
- Provide clear, step-by-step instructions
- Include estimated cooking and prep times
- Always include food_item_id for each ingredient used

Please respond with a complete recipe in JSON format."""

        return prompt

    @staticmethod
    def _build_user_context(user: UserRead) -> str:
        """Build user-specific context section."""
        context = f"USER PROFILE:\n- Name: {user.name}"

        if user.diet_type:
            context += f"\n- Diet Type: {user.diet_type}"

        if user.allergies:
            context += f"\n- Allergies: {user.allergies}"

        if user.preferences:
            context += f"\n- Preferences: {user.preferences}"

        return context

    @staticmethod
    def _build_inventory_context_enhanced(context: PromptContext) -> str:
        """Build enhanced inventory context with prioritization."""
        if not context.inventory_items:
            return "AVAILABLE INGREDIENTS:\nNo ingredients currently available in the kitchen inventory."

        context_lines = [
            "AVAILABLE INGREDIENTS (with database IDs for reference):"
        ]

        # Sort items: expiring first, then low stock, then regular
        sorted_items = sorted(
            context.inventory_items,
            key=lambda x: (
                not x.expires_soon,  # Expiring items first
                not x.is_low_stock,  # Low stock items second
                x.food_item.name  # Alphabetical for rest
            )
        )

        for item in sorted_items:
            food_item = item.food_item
            base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
            quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"

            # Build ingredient line with status indicators
            ingredient_line = f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name}"

            # Add priority indicators
            status_indicators = []
            if item.expires_soon:
                days_left = (item.expiration_date - datetime.date.today()).days if item.expiration_date else None
                status_indicators.append(f"⚠️ EXPIRES IN {days_left} DAYS")
            elif item.is_expired:
                status_indicators.append("❌ EXPIRED")

            if item.is_low_stock:
                status_indicators.append("📉 LOW STOCK")

            if status_indicators:
                ingredient_line += f" | {' | '.join(status_indicators)}"
            elif item.expiration_date:
                ingredient_line += f" | Expires: {item.expiration_date.strftime('%Y-%m-%d')}"

            context_lines.append(ingredient_line)

        # Add category summary
        if context.available_categories:
            context_lines.append(f"\nAVAILABLE CATEGORIES: {', '.join(context.available_categories.keys())}")

        context_lines.append(
            "\nIMPORTANT: Always use the exact ID and name from this list when specifying ingredients in your recipe."
        )

        return "\n".join(context_lines)

    @staticmethod
    def _build_equipment_context_typed(
            appliances: list[ApplianceWithDeviceType],
            tools: list[KitchenToolWithDeviceType]
    ) -> str:
        """Build kitchen equipment context with typed schemas."""
        context = "AVAILABLE KITCHEN EQUIPMENT:"

        if appliances:
            context += "\n\nAppliances:"
            for appliance in appliances:
                context += f"\n- {appliance.display_name}"
                if appliance.capacity_liters:
                    context += f" ({appliance.capacity_liters}L capacity)"
                # Use correct attribute names from schema
                if hasattr(appliance, 'device_type_name'):
                    context += f" | Type: {appliance.device_type_name}"

        if tools:
            context += "\n\nTools:"
            for tool in tools:
                tool_desc = f"- {tool.name}"
                if tool.size_or_detail:
                    tool_desc += f" ({tool.size_or_detail})"
                if tool.quantity and tool.quantity > 1:
                    tool_desc += f" (x{tool.quantity})"
                # Use correct attribute names from schema
                if hasattr(tool, 'device_type_name'):
                    tool_desc += f" | Type: {tool.device_type_name}"
                context += f"\n{tool_desc}"

        if not appliances and not tools:
            context += "\n- Basic cooking equipment assumed"

        return context

    @staticmethod
    def _build_priority_context(context: PromptContext) -> str:
        """Build priority context for ingredient usage."""
        priority_lines = []

        if context.request.prioritize_expiring and context.expiring_items:
            priority_lines.append("PRIORITY INGREDIENTS (use these first):")
            for item in context.expiring_items:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"
                days_left = (item.expiration_date - datetime.date.today()).days if item.expiration_date else None
                priority_lines.append(
                    f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name} - expires in {days_left} days")

        if context.low_stock_items:
            if priority_lines:
                priority_lines.append("")
            priority_lines.append("LOW STOCK ITEMS (use sparingly):")
            for item in context.low_stock_items:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"
                priority_lines.append(f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name}")

        # Add appliance preferences
        if context.request.required_appliances:
            if priority_lines:
                priority_lines.append("")
            priority_lines.append(f"REQUIRED APPLIANCES: {', '.join(context.request.required_appliances)}")

        if context.request.avoid_appliances:
            if priority_lines:
                priority_lines.append("")
            priority_lines.append(f"AVOID APPLIANCES: {', '.join(context.request.avoid_appliances)}")

        return "\n".join(priority_lines) if priority_lines else "No special priorities specified."

    @staticmethod
    def _build_request_context(request: RecipeGenerationRequest) -> str:
        """Build request-specific context section."""
        context = "RECIPE REQUEST:"

        if request.cuisine_type:
            context += f"\n- Cuisine: {request.cuisine_type}"

        if request.meal_type:
            context += f"\n- Meal Type: {request.meal_type}"

        if request.difficulty_level:
            context += f"\n- Difficulty: {request.difficulty_level}"

        if request.max_prep_time:
            context += f"\n- Max Prep Time: {request.max_prep_time} minutes"

        if request.max_cook_time:
            context += f"\n- Max Cook Time: {request.max_cook_time} minutes"

        if request.servings:
            context += f"\n- Servings: {request.servings}"

        if request.dietary_restrictions:
            context += f"\n- Dietary Restrictions: {', '.join(request.dietary_restrictions)}"

        if request.exclude_ingredients:
            context += f"\n- Exclude: {', '.join(request.exclude_ingredients)}"

        if request.special_requests:
            context += f"\n- Special Requests: {request.special_requests}"

        # Add new contextual preferences
        preferences = []
        if request.prioritize_expiring:
            preferences.append("prioritize expiring ingredients")
        if request.prefer_available_ingredients:
            preferences.append("prefer available ingredients")

        if preferences:
            context += f"\n- Preferences: {', '.join(preferences)}"

        return context

    def build_inventory_analysis_prompt(self, kitchen_id: int) -> tuple[str, str]:
        """Build prompts for inventory analysis using structured context."""

        # Create a minimal request for analysis
        analysis_request = RecipeGenerationRequest(
            special_requests="Analyze inventory for insights and recommendations"
        )

        # Build context (user_id=1 is placeholder for analysis)
        context = PromptContext.build_from_ids(
            db=self.db,
            user_id=1,  # Placeholder - analysis doesn't need specific user
            kitchen_id=kitchen_id,
            request=analysis_request
        )

        system_prompt = """You are NUGAMOTO, a smart kitchen inventory assistant.

Analyze the provided inventory and provide insights including:
- Items that are expiring soon or already expired
- Suggested recipes to use expiring ingredients
- Items that are running low on stock
- Food waste reduction recommendations
- Shopping suggestions for missing staples

Respond in JSON format with structured analysis."""

        # Build comprehensive analysis prompt
        analysis_sections = []

        if context.expiring_items:
            analysis_sections.append("EXPIRING SOON:")
            for item in context.expiring_items:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                days_left = (item.expiration_date - datetime.date.today()).days if item.expiration_date else None
                analysis_sections.append(
                    f"- {food_item.name}: {item.quantity} {base_unit_name} (expires in {days_left} days)")

        if context.low_stock_items:
            analysis_sections.append("\nLOW STOCK:")
            for item in context.low_stock_items:
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                analysis_sections.append(f"- {food_item.name}: {item.quantity} {base_unit_name} (below minimum)")

        # Good condition items
        good_items = [
            item for item in context.inventory_items
            if not item.expires_soon and not item.is_low_stock and not item.is_expired
        ]

        if good_items:
            analysis_sections.append("\nGOOD CONDITION:")
            for item in good_items[:10]:  # Limit to first 10
                food_item = item.food_item
                base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
                analysis_sections.append(f"- {food_item.name}: {item.quantity} {base_unit_name}")

        if context.available_categories:
            analysis_sections.append(f"\nAVAILABLE CATEGORIES: {', '.join(context.available_categories.keys())}")

        user_prompt = f"""Please analyze this kitchen inventory:

{chr(10).join(analysis_sections)}

Provide a comprehensive analysis with recommendations for optimal ingredient usage and waste reduction."""

        return system_prompt, user_prompt