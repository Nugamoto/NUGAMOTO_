"""AI Recipe generation page for NUGAMOTO frontend."""

import os
import sys
from typing import Dict, Any

import streamlit as st

# Add frontend to path for runtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Direct imports for IDE resolution
try:
    from clients import AIRecipesClient, RecipesClient, APIException
    from components.recipe_components import (
        display_ai_recipe_generation_form,
        display_recipe_ingredients,
        display_recipe_steps,
        display_recipe_nutrition,
    )
except ImportError:
    # Try absolute imports if relative fail
    import sys
    import os

    # Get the parent directory (frontend)
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from clients import AIRecipesClient, RecipesClient, APIException
    from components.recipe_components import (
        display_ai_recipe_generation_form,
        display_recipe_ingredients,
        display_recipe_steps,
        display_recipe_nutrition,
    )


def show_ai_recipe_generator():
    """Display AI recipe generation form and handle results."""
    st.title("🤖 AI Recipe Generator")
    st.markdown(
        "Let our AI create a personalized recipe based on your preferences "
        "and available ingredients!"
    )

    # Initialize clients
    if 'ai_recipes_client' not in st.session_state:
        st.session_state.ai_recipes_client = AIRecipesClient()
        if hasattr(st.session_state, 'access_token'):
            st.session_state.ai_recipes_client.set_tokens(
                st.session_state.access_token,
                getattr(st.session_state, 'refresh_token', None)
            )

    if 'recipes_client' not in st.session_state:
        st.session_state.recipes_client = RecipesClient()
        if hasattr(st.session_state, 'access_token'):
            st.session_state.recipes_client.set_tokens(
                st.session_state.access_token,
                getattr(st.session_state, 'refresh_token', None)
            )

    # Check if user is logged in
    if not hasattr(st.session_state, 'current_user') or not hasattr(st.session_state, 'selected_kitchen_id'):
        st.warning("⚠️ You must be logged in and have a kitchen selected to generate AI recipes.")
        return

    user_id = st.session_state.current_user.get('id')
    kitchen_id = st.session_state.selected_kitchen_id

    # Generation form
    recipe_request = display_ai_recipe_generation_form()

    if recipe_request:
        try:
            with st.spinner("🤖 AI is generating your recipe... This may take a moment."):
                # Generate recipe
                ai_result = st.session_state.ai_recipes_client.generate_recipe(
                    user_id=user_id,
                    kitchen_id=kitchen_id,
                    recipe_request=recipe_request
                )

            # Store AI result in session state
            st.session_state.ai_generated_recipe = ai_result
            st.success("🎉 Recipe generated successfully!")
            st.rerun()

        except Exception as e:
            st.error(f"Error generating recipe: {str(e)}")
            st.info("Please try again or modify your parameters.")

    # Display generated recipe if available
    if hasattr(st.session_state, 'ai_generated_recipe'):
        display_generated_recipe(st.session_state.ai_generated_recipe, user_id)


def display_generated_recipe(ai_result: Dict[str, Any], user_id: int):
    """Display the AI-generated recipe with save option."""
    st.divider()
    st.header("🤖 Generated Recipe")

    recipe_data = ai_result.get("recipe", {})
    ai_output = ai_result.get("ai_output", {})
    ai_output_id = ai_output.get("id")

    if not recipe_data:
        st.error("Error: Recipe data not available.")
        return

    # Recipe header
    st.subheader(recipe_data.get("title", "Unknown Recipe"))

    if recipe_data.get("description"):
        st.markdown(f"*{recipe_data['description']}*")

    # Recipe metadata
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if recipe_data.get("cuisine_type"):
            st.info(f"🍽️ {recipe_data['cuisine_type'].title()}")

    with col2:
        if recipe_data.get("meal_type"):
            st.info(f"🕐 {recipe_data['meal_type'].title()}")

    with col3:
        difficulty = recipe_data.get("difficulty", "medium")
        difficulty_icons = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
        icon = difficulty_icons.get(difficulty.lower(), "🟡")
        st.info(f"{icon} {difficulty.title()}")

    with col4:
        if recipe_data.get("servings"):
            st.info(f"👥 {recipe_data['servings']} servings")

    # Time information
    if any([recipe_data.get("prep_time_minutes"), recipe_data.get("cook_time_minutes"),
            recipe_data.get("total_time_minutes")]):
        time_cols = st.columns(3)

        if recipe_data.get("prep_time_minutes"):
            time_cols[0].metric("⏱️ Prep Time", f"{recipe_data['prep_time_minutes']} min")

        if recipe_data.get("cook_time_minutes"):
            time_cols[1].metric("🔥 Cook Time", f"{recipe_data['cook_time_minutes']} min")

        if recipe_data.get("total_time_minutes"):
            time_cols[2].metric("⏰ Total Time", f"{recipe_data['total_time_minutes']} min")

    # Tags
    if recipe_data.get("tags"):
        tags_str = " ".join([f"#{tag}" for tag in recipe_data["tags"]])
        st.markdown(f"🏷️ **Tags:** {tags_str}")

    # Recipe content tabs
    tab1, tab2, tab3 = st.tabs(["🥘 Ingredients", "👩‍🍳 Instructions", "📊 Nutrition"])

    with tab1:
        ingredients = recipe_data.get("ingredients", [])
        display_recipe_ingredients(ingredients)

    with tab2:
        steps = recipe_data.get("steps", [])
        display_recipe_steps(steps)

    with tab3:
        nutrition = recipe_data.get("nutrition")
        display_recipe_nutrition(nutrition)

    # Save recipe section
    st.divider()
    st.subheader("💾 Save Recipe")
    st.info("Like the generated recipe? Save it to your recipe collection!")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("✅ Save Recipe", type="primary"):
            save_ai_recipe(ai_output_id, user_id)

    with col2:
        if st.button("🔄 Generate New Recipe"):
            # Clear the generated recipe
            if 'ai_generated_recipe' in st.session_state:
                del st.session_state.ai_generated_recipe
            st.rerun()

    with col3:
        st.write("")  # Empty column for spacing


def save_ai_recipe(ai_output_id: int, user_id: int):
    """Save the AI-generated recipe to the user's collection."""
    try:
        with st.spinner("Saving recipe..."):
            # Convert AI recipe to RecipeCreate format
            recipe_create_data = st.session_state.ai_recipes_client.convert_ai_recipe_to_create(
                ai_output_id=ai_output_id,
                user_id=user_id
            )

            # Create the recipe
            saved_recipe = st.session_state.recipes_client.create_recipe(recipe_create_data)
            recipe_id = saved_recipe.get("id")

            if recipe_id:
                # Mark AI output as saved
                st.session_state.ai_recipes_client.mark_ai_recipe_as_saved(
                    ai_output_id=ai_output_id,
                    recipe_id=recipe_id,
                    user_id=user_id
                )

                st.success("🎉 Recipe saved successfully!")
                st.info(f"You can now find the recipe in your collection with ID {recipe_id}.")

                # Option to view the saved recipe
                if st.button("📖 View Saved Recipe"):
                    st.session_state.selected_recipe_id = recipe_id
                    # Clear AI recipe and switch to recipes page
                    if 'ai_generated_recipe' in st.session_state:
                        del st.session_state.ai_generated_recipe
                    st.switch_page("pages/recipes.py")
            else:
                st.error("Error: Recipe ID not available after saving.")

    except Exception as e:
        st.error(f"Error saving recipe: {str(e)}")
        st.info("Please try again.")


def show_recent_ai_recipes():
    """Display recently generated AI recipes for the current user."""
    st.header("🤖 Recent AI Recipes")

    try:
        # Get AI-generated recipes
        ai_recipes = st.session_state.recipes_client.get_ai_generated_recipes(limit=10)

        if not ai_recipes:
            st.info("No AI recipes generated yet. Create your first recipe!")
            return

        # Filter by current user if possible (this would need additional backend support)
        st.success(f"📚 {len(ai_recipes)} AI-generated recipes found")

        for recipe in ai_recipes:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.subheader(recipe.get("title", "Unknown Recipe"))
                    if recipe.get("description"):
                        st.write(recipe["description"])

                with col2:
                    if recipe.get("cuisine_type"):
                        st.write(f"🍽️ **Cuisine:** {recipe['cuisine_type'].title()}")

                    difficulty = recipe.get("difficulty", "medium")
                    difficulty_icons = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
                    icon = difficulty_icons.get(difficulty.lower(), "🟡")
                    st.write(f"{icon} **Difficulty:** {difficulty.title()}")

                with col3:
                    if st.button("Details", key=f"ai_recipe_{recipe.get('id')}"):
                        st.session_state.selected_recipe_id = recipe["id"]
                        st.switch_page("pages/recipes.py")

                st.divider()

    except Exception as e:
        st.error(f"Error loading AI recipes: {str(e)}")


def show_ai_recipes():
    """Main AI recipes page controller."""
    # Navigation tabs
    tab1, tab2 = st.tabs(["🤖 Generator", "📚 AI Recipes"])

    with tab1:
        show_ai_recipe_generator()

    with tab2:
        show_recent_ai_recipes()


if __name__ == "__main__":
    show_ai_recipes()
