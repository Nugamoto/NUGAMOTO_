"""Dynamic prompt builder for AI services."""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.crud import device as crud_device
from app.crud import inventory as crud_inventory
from app.crud import user as crud_user
from app.models.inventory import InventoryItem
from app.models.user import User
from app.schemas.ai_service import RecipeGenerationRequest


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
        # Get user data using correct CRUD function
        user = crud_user.get_user_by_id(self.db, user_id=user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get kitchen inventory using correct CRUD function
        inventory_items = crud_inventory.get_kitchen_inventory(
            self.db, kitchen_id=kitchen_id
        )

        # Get available appliances and tools using correct CRUD functions
        # These return the extended schemas with device type info
        appliances = crud_device.get_kitchen_appliances(
            self.db, kitchen_id=kitchen_id
        )
        tools = crud_device.get_kitchen_tools(
            self.db, kitchen_id=kitchen_id
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
        return """

You are NUGAMOTO, an expert culinary AI assistant specializing in smart kitchen management.

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
"""

    def _build_user_prompt(
            self,
            request: RecipeGenerationRequest,
            user: User,
            inventory_items: list[InventoryItem],
            appliances: list,  # Any type, could be ApplianceWithDeviceType
            tools: list       # Any type, could be KitchenToolWithDeviceType
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

    def _build_user_context(self, user: User) -> str:
        """Build user-specific context section."""
        context = f"USER PROFILE:\n- Name: {user.name}"

        if user.diet_type:
            context += f"\n- Diet Type: {user.diet_type}"

        if user.allergies:
            context += f"\n- Allergies: {user.allergies}"

        if user.preferences:
            context += f"\n- Preferences: {user.preferences}"

        return context

    def _build_inventory_context(self, inventory_items: list[InventoryItem]) -> str:
        """Build inventory context with food item IDs for AI prompts."""
        if not inventory_items:
            return "AVAILABLE INGREDIENTS:\nNo ingredients currently available in the kitchen inventory."

        # Group by category and include IDs
        context_lines = [
            "AVAILABLE INGREDIENTS (with database IDs for reference):"
        ]

        for item in inventory_items:
            food_item = item.food_item
            base_unit_name = food_item.base_unit.name if food_item.base_unit else 'units'
            quantity_str = f"{item.quantity:.1f}" if item.quantity % 1 != 0 else f"{int(item.quantity)}"

            ingredient_line = f"- {food_item.name} (ID: {food_item.id}): {quantity_str} {base_unit_name}"

            if item.expiration_date:
                ingredient_line += f" | Expires: {item.expiration_date.strftime('%Y-%m-%d')}"

            context_lines.append(ingredient_line)

        context_lines.append(
            "\nIMPORTANT: Always use the exact ID and name from this list when specifying ingredients in your recipe."
        )

        return "\n".join(context_lines)

    def _build_equipment_context(self, appliances: list, tools: list) -> str:
        """Build kitchen equipment context section."""
        context = "AVAILABLE KITCHEN EQUIPMENT:"

        if appliances:
            context += "\n\nAppliances:"
            for appliance in appliances:
                # Handle both Appliance and ApplianceWithDeviceType objects
                display_name = getattr(appliance, 'display_name', 'Unknown Appliance')
                capacity = getattr(appliance, 'capacity_liters', None)

                context += f"\n- {display_name}"
                if capacity:
                    context += f" ({capacity}L capacity)"

        if tools:
            context += "\n\nTools:"
            for tool in tools:
                # Handle both KitchenTool and KitchenToolWithDeviceType objects
                name = getattr(tool, 'name', 'Unknown Tool')
                size_detail = getattr(tool, 'size_or_detail', None)
                quantity = getattr(tool, 'quantity', None)

                tool_desc = f"- {name}"
                if size_detail:
                    tool_desc += f" ({size_detail})"
                if quantity and quantity > 1:
                    tool_desc += f" (x{quantity})"
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

    def build_inventory_analysis_prompt(self, kitchen_id: int) -> tuple[str, str]:
        """Build prompts for inventory analysis.

        Args:
            kitchen_id: ID of the kitchen to analyze.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        # Get inventory using correct CRUD function
        inventory_items = crud_inventory.get_kitchen_inventory(
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
            # Get base unit name from the relationship
            base_unit_name = item.food_item.base_unit.name if item.food_item.base_unit else 'units'

            if item.is_expired():
                expired_items.append(f"- {item.food_item.name}: {item.quantity} {base_unit_name} (expired {item.expiration_date})")
            elif item.expires_soon():
                days_left = (item.expiration_date - today).days if item.expiration_date else None
                expiring_items.append(f"- {item.food_item.name}: {item.quantity} {base_unit_name} (expires in {days_left} days)")
            elif item.is_low_stock():
                low_stock_items.append(f"- {item.food_item.name}: {item.quantity} {base_unit_name} (below minimum)")
            else:
                good_items.append(f"- {item.food_item.name}: {item.quantity} {base_unit_name}")

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