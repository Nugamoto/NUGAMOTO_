"""Dynamic prompt builder for AI services."""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.crud import inventory as crud_inventory
from app.crud import device as crud_device
from app.crud import user as crud_user
from app.schemas.ai_service import RecipeGenerationRequest
from app.schemas.user import UserRead
from app.schemas.inventory import InventoryItemRead
from app.schemas.device import ApplianceRead, KitchenToolRead


class PromptBuilder:
    """Builder for dynamic AI prompts based on user data and kitchen state."""

    def __init__(self, db: Session):
        """Initialize prompt builder with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    async def build_recipe_prompt(
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
        # Get user data
        user = await crud_user.get(self.db, id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get kitchen inventory
        inventory_items = await crud_inventory.get_kitchen_inventory(
            self.db, kitchen_id=kitchen_id
        )

        # Get available appliances and tools
        appliances = await crud_device.get_appliances_by_kitchen_id(
            self.db, kitchen_id=kitchen_id, available_only=True
        )
        tools = await crud_device.get_kitchen_tools_by_kitchen_id(
            self.db, kitchen_id=kitchen_id, available_only=True
        )

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            request=request,
            user=user,
            inventory_items=inventory_items,
            appliances=appliances,
            tools=tools
        )

        return system_prompt, user_prompt

    def _build_system_prompt(self) -> str:
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

Provide responses in valid JSON format with the specified schema."""

    def _build_user_prompt(
            self,
            request: RecipeGenerationRequest,
            user: UserRead,
            inventory_items: list[InventoryItemRead],
            appliances: list[ApplianceRead],
            tools: list[KitchenToolRead]
    ) -> str:
        """Build the user prompt with all contextual information."""

        # Build user context
        user_context = self._build_user_context(user)

        # Build inventory context
        inventory_context = self._build_inventory_context(inventory_items)

        # Build equipment context
        equipment_context = self._build_equipment_context(appliances, tools)

        # Build request context
        request_context = self._build_request_context(request)

        prompt = f"""Please generate a recipe based on the following information:

{user_context}

{inventory_context}

{equipment_context}

{request_context}

Requirements:
- Use available ingredients efficiently
- Consider dietary preferences and restrictions
- Suggest appropriate cooking methods for available equipment
- Provide clear, step-by-step instructions
- Include estimated cooking and prep times
- Mention any ingredient substitutions if needed

Please respond with a complete recipe in JSON format."""

        return prompt

    def _build_user_context(self, user: UserRead) -> str:
        """Build user-specific context section."""
        context = f"USER PROFILE:\n- Name: {user.name}"

        if user.diet_type:
            context += f"\n- Diet Type: {user.diet_type}"

        if user.allergies:
            context += f"\n- Allergies: {user.allergies}"

        if user.preferences:
            context += f"\n- Preferences: {user.preferences}"

        return context

    def _build_inventory_context(self, inventory_items: list[InventoryItemRead]) -> str:
        """Build inventory context section."""
        if not inventory_items:
            return "AVAILABLE INGREDIENTS:\n- No ingredients currently in inventory"

        context = "AVAILABLE INGREDIENTS:"

        # Group by categories and highlight expiring items
        today = datetime.date.today()
        expiring_soon = []
        regular_items = []

        for item in inventory_items:
            item_desc = f"- {item.food_item.name}: {item.quantity} {item.base_unit_name or 'units'}"

            if item.expiration_date and (item.expiration_date - today).days <= 3:
                expiring_soon.append(f"{item_desc} (expires {item.expiration_date})")
            else:
                regular_items.append(item_desc)

        if expiring_soon:
            context += "\n\nEXPIRING SOON (prioritize these):"
            context += "\n" + "\n".join(expiring_soon)

        if regular_items:
            context += "\n\nOTHER AVAILABLE:"
            context += "\n" + "\n".join(regular_items)

        return context

    def _build_equipment_context(
            self,
            appliances: list[ApplianceRead],
            tools: list[KitchenToolRead]
    ) -> str:
        """Build kitchen equipment context section."""
        context = "AVAILABLE KITCHEN EQUIPMENT:"

        if appliances:
            context += "\n\nAppliances:"
            for appliance in appliances:
                context += f"\n- {appliance.display_name}"
                if appliance.capacity_liters:
                    context += f" ({appliance.capacity_liters}L capacity)"

        if tools:
            context += "\n\nTools:"
            for tool in tools:
                tool_desc = f"- {tool.name}"
                if tool.size_or_detail:
                    tool_desc += f" ({tool.size_or_detail})"
                if tool.quantity and tool.quantity > 1:
                    tool_desc += f" (x{tool.quantity})"
                context += f"\n{tool_desc}"

        if not appliances and not tools:
            context += "\n- Basic cooking equipment assumed"

        return context

    def _build_request_context(self, request: RecipeGenerationRequest) -> str:
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

        return context

    async def build_inventory_analysis_prompt(self, kitchen_id: int) -> tuple[str, str]:
        """Build prompts for inventory analysis.

        Args:
            kitchen_id: ID of the kitchen to analyze.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        inventory_items = await crud_inventory.get_kitchen_inventory(
            self.db, kitchen_id=kitchen_id
        )

        system_prompt = """You are NUGAMOTO, a smart kitchen inventory assistant.

Analyze the provided inventory and provide insights including:
- Items that are expiring soon or already expired
- Suggested recipes to use expiring ingredients
- Items that are running low on stock
- Food waste reduction recommendations
- Shopping suggestions for missing staples

Respond in JSON format with structured analysis."""

        # Build inventory analysis
        today = datetime.date.today()
        expired_items = []
        expiring_items = []
        low_stock_items = []
        good_items = []

        for item in inventory_items:
            if item.is_expired:
                expired_items.append(f"- {item.food_item.name}: {item.quantity} {item.base_unit_name or 'units'} (expired {item.expiration_date})")
            elif item.expires_soon:
                days_left = (item.expiration_date - today).days if item.expiration_date else None
                expiring_items.append(f"- {item.food_item.name}: {item.quantity} {item.base_unit_name or 'units'} (expires in {days_left} days)")
            elif item.is_low_stock:
                low_stock_items.append(f"- {item.food_item.name}: {item.quantity} {item.base_unit_name or 'units'} (below minimum)")
            else:
                good_items.append(f"- {item.food_item.name}: {item.quantity} {item.base_unit_name or 'units'}")

        user_prompt = "Please analyze this kitchen inventory:\n\n"

        if expired_items:
            user_prompt += "EXPIRED ITEMS:\n" + "\n".join(expired_items) + "\n\n"

        if expiring_items:
            user_prompt += "EXPIRING SOON:\n" + "\n".join(expiring_items) + "\n\n"

        if low_stock_items:
            user_prompt += "LOW STOCK:\n" + "\n".join(low_stock_items) + "\n\n"

        if good_items:
            user_prompt += "GOOD CONDITION:\n" + "\n".join(good_items) + "\n\n"

        user_prompt += "Provide a comprehensive analysis with recommendations for optimal ingredient usage and waste reduction."

        return system_prompt, user_prompt