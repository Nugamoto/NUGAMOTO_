"""Interactive test script for AI service."""

import asyncio
import logging
import sys
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    return RecipeGenerationRequest(
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


async def interactive_test():
    """Interactive test with user selection."""
    if not settings.OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        return

    db: Session = SessionLocal()

    try:
        print("🤖 NUGAMOTO AI Service - Interactive Test")
        print("=" * 50)

        # Get users
        users = crud_user.get_all_users(db)
        if not users:
            print("❌ No users found in database.")
            return

        print("\n👥 Available users:")
        for i, user in enumerate(users, 1):
            print(f"{i}. {user.name} ({user.email})")

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

        print(f"✅ Selected user: {selected_user.name}")

        # Get user's kitchens
        user_kitchens = crud_kitchen.get_user_kitchens(db, user_id=selected_user.id)
        if not user_kitchens:
            print(f"⚠️  User has no kitchens.")
            return

        print("\n🏠 User's kitchens:")
        kitchens = [uk.kitchen for uk in user_kitchens]
        for i, kitchen in enumerate(kitchens, 1):
            print(f"{i}. {kitchen.name}")

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

        print(f"✅ Selected kitchen: {selected_kitchen.name}")

        # Create recipe request
        recipe_request = create_recipe_request()

        # Generate recipe
        print(f"\n🔄 Generating recipe...")
        ai_service = OpenAIService(db=db)

        recipe = await ai_service.generate_recipe(
            request=recipe_request,
            user_id=selected_user.id,
            kitchen_id=selected_kitchen.id
        )

        # Display results
        print("\n" + "="*80)
        print("🎉 RECIPE GENERATION SUCCESSFUL!")
        print("="*80)
        print(f"📋 Title: {recipe.title}")
        print(f"🍽️  Cuisine: {recipe.cuisine_type}")
        print(f"⏱️  Total Time: {recipe.total_time_minutes} minutes")
        print(f"👥 Servings: {recipe.servings}")
        print(f"📊 Difficulty: {recipe.difficulty_level}")

        print(f"\n📝 Description:")
        print(f"   {recipe.description or 'No description provided'}")

        print(f"\n🥘 Ingredients ({len(recipe.ingredients)}):")
        for ingredient in recipe.ingredients:
            print(f"   • {ingredient.amount} {ingredient.name}")

        print(f"\n👩‍🍳 Instructions ({len(recipe.instructions)} steps):")
        for instruction in recipe.instructions:
            time_info = f" ({instruction.estimated_time} min)" if instruction.estimated_time else ""
            print(f"   {instruction.step_number}. {instruction.instruction}{time_info}")

        if recipe.tips:
            print(f"\n💡 Tips:")
            for tip in recipe.tips:
                print(f"   • {tip}")

        if recipe.tags:
            print(f"\n🏷️  Tags: {', '.join(recipe.tags)}")

        print("="*80)

    except OpenAIServiceError as e:
        print(f"\n❌ AI Service Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.exception("Full error details:")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(interactive_test())