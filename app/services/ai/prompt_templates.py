"""Prompt templates and constants for AI services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


# ================================================================== #
# Global Prompt Constants                                            #
# ================================================================== #

# System Prompts
NUGAMOTO_RECIPE_SYSTEM_PROMPT = """You are NUGAMOTO, an expert culinary AI assistant specializing in smart kitchen management.

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

NUGAMOTO_INVENTORY_SYSTEM_PROMPT = """You are NUGAMOTO, a smart kitchen inventory assistant.

Analyze the provided inventory and provide insights including:
- Items that are expiring soon or already expired
- Suggested recipes to use expiring ingredients
- Items that are running low on stock
- Food waste reduction recommendations
- Shopping suggestions for missing staples

Respond in JSON format with structured analysis."""

NUGAMOTO_SUGGESTIONS_SYSTEM_PROMPT = """You are NUGAMOTO, a personalized cooking assistant.

Provide 3-5 quick meal suggestions in JSON format with the following structure:
{
    "suggestions": [
        {
            "title": "Recipe title",
            "description": "Brief description",
            "estimated_time": "Total time in minutes",
            "difficulty": "easy/medium/hard",
            "main_ingredients": ["ingredient1", "ingredient2"]
        }
    ]
}

Focus on practical, achievable meals based on available ingredients."""

# Section Headers
SECTION_HEADERS = {
    "user_profile": "USER PROFILE:",
    "available_ingredients": "AVAILABLE INGREDIENTS (with database IDs for reference):",
    "available_equipment": "AVAILABLE KITCHEN EQUIPMENT:",
    "priority_ingredients": "PRIORITY INGREDIENTS (use these first):",
    "low_stock_items": "LOW STOCK ITEMS (use sparingly):",
    "recipe_request": "RECIPE REQUEST:",
    "requirements": "Requirements:",
    "expiring_soon": "EXPIRING SOON:",
    "good_condition": "GOOD CONDITION:",
    "available_categories": "AVAILABLE CATEGORIES:",
}

# Status Indicators
STATUS_INDICATORS = {
    "expires_soon": "⚠️ EXPIRES IN {days} DAYS",
    "expired": "❌ EXPIRED",
    "low_stock": "📉 LOW STOCK",
}

# Common Requirements
RECIPE_REQUIREMENTS = [
    "Use available ingredients efficiently",
    "Consider dietary preferences and restrictions",
    "PRIORITIZE expiring ingredients when possible",
    "Suggest appropriate cooking methods for available equipment",
    "Provide clear, step-by-step instructions",
    "Include estimated cooking and prep times",
    "Always include food_item_id for each ingredient used",
]

# Common Messages
COMMON_MESSAGES = {
    "no_ingredients": "No ingredients currently available in the kitchen inventory.",
    "basic_equipment": "Basic cooking equipment assumed",
    "no_priorities": "No special priorities specified.",
    "important_ids": "IMPORTANT: Always use the exact ID and name from this list when specifying ingredients in your recipe.",
    "json_format": "Please respond with a complete recipe in JSON format.",
}


# ================================================================== #
# Template Protocols                                                 #
# ================================================================== #

class PromptSectionBuilder(Protocol):
    """Protocol for prompt section builders."""
    
    def build_section(self, context: dict) -> str:
        """Build a specific section of the prompt."""
        ...


# ================================================================== #
# Template Dataclasses                                              #
# ================================================================== #

@dataclass
class PromptTemplate:
    """Template for structured prompt generation."""
    
    system_prompt: str
    user_template: str
    requirements: list[str]
    
    def format_user_prompt(self, **kwargs) -> str:
        """Format user prompt with provided context."""
        return self.user_template.format(**kwargs)
    
    def build_complete_prompt(self, **kwargs) -> tuple[str, str]:
        """Build complete system and user prompts."""
        user_prompt = self.format_user_prompt(**kwargs)
        return self.system_prompt, user_prompt


@dataclass
class SectionTemplate:
    """Template for individual prompt sections."""
    
    header: str
    format_string: str
    fallback_message: str = ""
    
    def build(self, data: dict) -> str:
        """Build section with provided data."""
        if not data:
            return f"{self.header}\n{self.fallback_message}" if self.fallback_message else ""
        
        return f"{self.header}\n{self.format_string.format(**data)}"


# ================================================================== #
# Predefined Templates                                              #
# ================================================================== #

RECIPE_GENERATION_TEMPLATE = PromptTemplate(
    system_prompt=NUGAMOTO_RECIPE_SYSTEM_PROMPT,
    user_template="""Please generate a recipe based on the following information:

{user_context}

{inventory_context}

{equipment_context}

{priority_context}

{request_context}

{requirements}

{closing_message}""",
    requirements=RECIPE_REQUIREMENTS
)

INVENTORY_ANALYSIS_TEMPLATE = PromptTemplate(
    system_prompt=NUGAMOTO_INVENTORY_SYSTEM_PROMPT,
    user_template="""Please analyze this kitchen inventory:

{analysis_sections}

Provide a comprehensive analysis with recommendations for optimal ingredient usage and waste reduction.""",
    requirements=[]
)

COOKING_SUGGESTIONS_TEMPLATE = PromptTemplate(
    system_prompt=NUGAMOTO_SUGGESTIONS_SYSTEM_PROMPT,
    user_template="""Based on the following kitchen information:

{user_context}

{inventory_context}

{equipment_context}

Please provide quick meal suggestions rather than a single detailed recipe.""",
    requirements=[]
)


# ================================================================== #
# Section Templates                                                  #
# ================================================================== #

USER_PROFILE_TEMPLATE = SectionTemplate(
    header=SECTION_HEADERS["user_profile"],
    format_string="- Name: {name}\n- Diet Type: {diet_type}\n- Allergies: {allergies}\n- Preferences: {preferences}",
    fallback_message="No user profile information available."
)

INVENTORY_TEMPLATE = SectionTemplate(
    header=SECTION_HEADERS["available_ingredients"],
    format_string="{ingredient_list}\n\n{category_summary}\n\n{important_message}",
    fallback_message=COMMON_MESSAGES["no_ingredients"]
)

EQUIPMENT_TEMPLATE = SectionTemplate(
    header=SECTION_HEADERS["available_equipment"],
    format_string="{appliances_section}\n\n{tools_section}",
    fallback_message=f"- {COMMON_MESSAGES['basic_equipment']}"
)
