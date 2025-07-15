
"""Interactive test script for AI service."""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.ai_service import RecipeGenerationRequest
from app.services.ai.openai_service import OpenAIService, OpenAIServiceError
from app.core.enums import DifficultyLevel
from app.crud import user as crud_user
from app.crud import kitchen as crud_kitchen
from app.crud import food as crud_food
from app.crud import core as crud_core

# Configure logging with separate levels for file and console
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create timestamp for log filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = log_dir / f"ai_test_{timestamp}.log"

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# File handler (DEBUG level - alles)
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Console handler (INFO level - nur wichtige Infos)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Add handlers to root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
print(f"📝 Detailed logs will be saved to: {log_filename}")


def create_recipe_request() -> RecipeGenerationRequest:
    """Interactively create a recipe request."""
    print("\n🍳 Let's create a recipe request!")
    print("-" * 40)

    cuisine_type = input("Cuisine type (e.g., italian, asian, mexican) [optional]: ").strip() or None
    meal_type = input("Meal type (breakfast, lunch, dinner, snack) [optional]: ").strip() or None

    # Difficulty
    print("Difficulty level:")
    print("1. Easy")
    print("2. Medium")
    print("3. Hard")
    difficulty_choice = input("Choose difficulty (1-3) [optional]: ").strip()
    difficulty_map = {
        "1": DifficultyLevel.EASY,
        "2": DifficultyLevel.MEDIUM,
        "3": DifficultyLevel.HARD
    }
    difficulty_level = difficulty_map.get(difficulty_choice)

    # Time constraints
    max_prep_time = None
    prep_input = input("Max prep time in minutes [optional]: ").strip()
    if prep_input.isdigit():
        max_prep_time = int(prep_input)

    max_cook_time = None
    cook_input = input("Max cook time in minutes [optional]: ").strip()
    if cook_input.isdigit():
        max_cook_time = int(cook_input)

    # Servings
    servings = None
    servings_input = input("Number of servings [optional]: ").strip()
    if servings_input.isdigit():
        servings = int(servings_input)

    # Dietary restrictions
    dietary_restrictions = []
    restrictions_input = input("Dietary restrictions (comma-separated, e.g., vegetarian, vegan) [optional]: ").strip()
    if restrictions_input:
        dietary_restrictions = [r.strip() for r in restrictions_input.split(",")]

    # Exclude ingredients
    exclude_ingredients = []
    exclude_input = input("Ingredients to exclude (comma-separated) [optional]: ").strip()
    if exclude_input:
        exclude_ingredients = [i.strip() for i in exclude_input.split(",")]

    # Special requests
    special_requests = input("Special requests or preferences [optional]: ").strip() or None

    recipe_request = RecipeGenerationRequest(
        cuisine_type=cuisine_type,
        meal_type=meal_type,
        difficulty_level=difficulty_level,
        max_prep_time=max_prep_time,
        max_cook_time=max_cook_time,
        servings=servings,
        dietary_restrictions=dietary_restrictions,
        exclude_ingredients=exclude_ingredients,
        special_requests=special_requests
    )

    # Log the created request
    logger.debug(f"Created recipe request: {recipe_request.model_dump()}")

    return recipe_request


def print_prompt_info(system_prompt: str, user_prompt: str):
    """Print the prompts that will be sent to the AI."""
    print("\n" + "=" * 80)
    print("📝 PROMPTS SENT TO OPENAI")
    print("=" * 80)

    print("\n🤖 SYSTEM PROMPT:")
    print("-" * 50)
    print(system_prompt)

    print("\n👤 USER PROMPT:")
    print("-" * 50)
    print(user_prompt)
    print("=" * 80)

    # Log the prompts to file
    logger.debug("=== SYSTEM PROMPT ===")
    logger.debug(system_prompt)
    logger.debug("=== USER PROMPT ===")
    logger.debug(user_prompt)


def print_structured_output(response_data: dict):
    """Print the structured output received from OpenAI."""
    print("\n" + "=" * 80)
    print("📊 STRUCTURED OUTPUT FROM OPENAI API")
    print("=" * 80)

    # Pretty print the JSON response
    formatted_json = json.dumps(response_data, indent=2, ensure_ascii=False)
    print(formatted_json)
    print("=" * 80)

    # Log the structured output to file
    logger.debug("=== STRUCTURED OUTPUT FROM OPENAI API ===")
    logger.debug(formatted_json)
    logger.debug("=== END STRUCTURED OUTPUT ===")


def format_ingredient_display(ingredient, db: Session) -> str:
    """Format ingredient for display with proper name and unit lookup."""
    try:
        # Look up food item name
        food_item = crud_food.get_food_item_by_id(db, food_item_id=ingredient.food_item_id)
        food_name = food_item.name if food_item else f"Food ID: {ingredient.food_item_id}"

        # Check if this is an AI ingredient (only has original_amount/original_unit_id)
        if hasattr(ingredient, 'original_amount') and hasattr(ingredient, 'original_unit_id'):
            # This is an AIRecipeIngredientCreate
            if ingredient.original_unit_id and ingredient.original_amount:
                original_unit = crud_core.get_unit_by_id(db, unit_id=ingredient.original_unit_id)
                original_unit_name = original_unit.name if original_unit else f"Unit ID: {ingredient.original_unit_id}"
                return f"{ingredient.original_amount} {original_unit_name} {food_name}"
            else:
                return f"? units {food_name}"

        # This is a regular RecipeIngredientCreate/Read with amount_in_base_unit
        elif hasattr(ingredient, 'amount_in_base_unit'):
            amount = ingredient.amount_in_base_unit
            base_unit = food_item.base_unit.name if food_item and food_item.base_unit else "units"

            # If original unit is specified, show both
            if hasattr(ingredient, 'original_unit_id') and ingredient.original_unit_id and ingredient.original_amount:
                original_unit = crud_core.get_unit_by_id(db, unit_id=ingredient.original_unit_id)
                original_unit_name = original_unit.name if original_unit else f"Unit ID: {ingredient.original_unit_id}"
                return f"{ingredient.original_amount} {original_unit_name} {food_name} ({amount} {base_unit})"
            else:
                return f"{amount} {base_unit} {food_name}"

        # Fallback
        else:
            return f"Unknown format: {food_name}"

    except Exception as e:
        logger.warning(f"Error formatting ingredient display: {e}")
        return f"Error displaying ingredient (Food ID: {ingredient.food_item_id})"

async def interactive_test():
    """Interactive test with user selection."""
    logger.info("Starting NUGAMOTO AI Service Interactive Test")

    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not found in environment variables")
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        return

    db: Session = SessionLocal()
    logger.debug("Database session created")

    try:
        print("🤖 NUGAMOTO AI Service - Interactive Test")
        print("=" * 50)

        # Get users
        logger.debug("Fetching all users from database")
        users = crud_user.get_all_users(db)
        if not users:
            logger.warning("No users found in database")
            print("❌ No users found in database.")
            return

        logger.info(f"Found {len(users)} users in database")
        print("\n👥 Available users:")
        for i, user in enumerate(users, 1):
            print(f"{i}. {user.name} ({user.email})")
            logger.debug(f"User {i}: {user.name} (ID: {user.id}, Email: {user.email})")

        # Select user
        while True:
            try:
                choice = int(input(f"\nSelect user (1-{len(users)}): "))
                if 1 <= choice <= len(users):
                    selected_user = users[choice - 1]
                    break
                print("Invalid choice, please try again.")
            except ValueError:
                print("Please enter a valid number.")

        logger.info(f"Selected user: {selected_user.name} (ID: {selected_user.id})")
        print(f"✅ Selected user: {selected_user.name}")

        # Get user's kitchens
        logger.debug(f"Fetching kitchens for user {selected_user.id}")
        user_kitchens = crud_kitchen.get_user_kitchens(db, user_id=selected_user.id)
        if not user_kitchens:
            logger.warning(f"User {selected_user.id} has no kitchens")
            print(f"⚠️  User has no kitchens.")
            return

        logger.info(f"Found {len(user_kitchens)} kitchens for user {selected_user.id}")
        print("\n🏠 User's kitchens:")
        kitchens = [uk.kitchen for uk in user_kitchens]
        for i, kitchen in enumerate(kitchens, 1):
            print(f"{i}. {kitchen.name}")
            logger.debug(f"Kitchen {i}: {kitchen.name} (ID: {kitchen.id})")

        # Select kitchen
        while True:
            try:
                choice = int(input(f"\nSelect kitchen (1-{len(kitchens)}): "))
                if 1 <= choice <= len(kitchens):
                    selected_kitchen = kitchens[choice - 1]
                    break
                print("Invalid choice, please try again.")
            except ValueError:
                print("Please enter a valid number.")

        logger.info(f"Selected kitchen: {selected_kitchen.name} (ID: {selected_kitchen.id})")
        print(f"✅ Selected kitchen: {selected_kitchen.name}")

        # Create recipe request
        logger.debug("Starting recipe request creation")
        recipe_request = create_recipe_request()

        # Generate recipe
        print(f"\n🔄 Generating recipe...")
        logger.info("Initializing OpenAI service")
        ai_service = OpenAIService(db=db)

        # Build the prompts to show them before making the API call
        logger.debug("Building prompts for OpenAI API")
        system_prompt, user_prompt = ai_service.prompt_builder.build_recipe_prompt(
            request=recipe_request,
            user_id=selected_user.id,
            kitchen_id=selected_kitchen.id
        )

        # Display the prompts
        print_prompt_info(system_prompt, user_prompt)

        # Ask user if they want to continue
        continue_choice = input("\n🔄 Do you want to proceed with the API call? (y/n): ").strip().lower()
        if continue_choice not in ['y', 'yes']:
            logger.info("API call cancelled by user")
            print("❌ API call cancelled by user.")
            return

        # Make the API call and capture the raw response
        print("\n🔄 Making API call to OpenAI...")
        logger.info("Starting recipe generation with OpenAI API")

        recipe = await ai_service.generate_recipe(
            request=recipe_request,
            user_id=selected_user.id,
            kitchen_id=selected_kitchen.id
        )

        # Convert the response back to dict for display
        response_data = recipe.model_dump()
        print_structured_output(response_data)

        # Display results
        logger.info("Recipe generation completed successfully")
        print("\n" + "="*80)
        print("🎉 RECIPE GENERATION SUCCESSFUL!")
        print("="*80)
        print(f"📋 Title: {recipe.title}")
        print(f"🍽️  Cuisine: {recipe.cuisine_type}")
        print(f"⏱️  Total Time: {recipe.total_time_minutes} minutes")
        print(f"👥 Servings: {recipe.servings}")
        print(f"📊 Difficulty: {recipe.difficulty}")

        print(f"\n📝 Description:")
        print(f"   {recipe.description or 'No description provided'}")

        print(f"\n🥘 Ingredients ({len(recipe.ingredients)}):")
        for ingredient in recipe.ingredients:
            # Use correct schema attributes and lookup names
            display_text = format_ingredient_display(ingredient, db)
            print(f"   • {display_text}")

        print(f"\n👩‍🍳 Instructions ({len(recipe.steps)} steps):")
        for step in recipe.steps:
            # Use correct schema attributes - no estimated_time_minutes
            print(f"   {step.step_number}. {step.instruction}")

        if recipe.tips:
            print(f"\n💡 Tips:")
            for tip in recipe.tips:
                print(f"   • {tip}")

        if recipe.tags:
            print(f"\n🏷️  Tags: {', '.join(recipe.tags)}")

        print("="*80)
        logger.info("Interactive test completed successfully")

    except OpenAIServiceError as e:
        logger.error(f"AI Service Error: {str(e)}", exc_info=True)
        print(f"\n❌ AI Service Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
    finally:
        logger.debug("Closing database session")
        db.close()
        logger.info("Interactive test session ended")


if __name__ == "__main__":
    asyncio.run(interactive_test())