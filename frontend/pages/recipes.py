"""Recipe management page for NUGAMOTO frontend."""

import os
import sys
from typing import Optional, Dict, Any

import streamlit as st

# Add frontend to path for runtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Direct imports for IDE resolution
try:
    from clients import RecipesClient, APIException
    from components.recipe_components import (
        display_recipe_card,
        display_recipe_ingredients,
        display_recipe_steps,
        display_recipe_nutrition,
        display_recipe_reviews,
        create_recipe_review_form,
        display_recipe_filter_sidebar,
        display_cook_recipe_button
    )
except ImportError:
    # Try absolute imports if relative fail
    import sys
    import os

    # Get the parent directory (frontend)
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

    from clients import RecipesClient, APIException
    from components.recipe_components import (
        display_recipe_card,
        display_recipe_ingredients,
        display_recipe_steps,
        display_recipe_nutrition,
        display_recipe_reviews,
        create_recipe_review_form,
        display_recipe_filter_sidebar,
        display_cook_recipe_button
    )


def show_recipe_list():
    """Display the main recipe list with filtering."""
    st.title("📖 Recipes")
    st.markdown("Discover delicious recipes or create your own!")

    # Initialize clients
    if 'recipes_client' not in st.session_state:
        st.session_state.recipes_client = RecipesClient()
        # Set tokens if available
        if hasattr(st.session_state, 'access_token'):
            st.session_state.recipes_client.set_tokens(
                st.session_state.access_token,
                getattr(st.session_state, 'refresh_token', None)
            )

    # Filter sidebar
    filters = display_recipe_filter_sidebar()

    try:
        # Load recipes with filters
        with st.spinner("Loading recipes..."):
            recipes = st.session_state.recipes_client.get_all_recipes(**filters)

        if not recipes:
            st.info("No recipes found. Try different filter criteria or create a new recipe!")
            return

        st.success(f"📚 {len(recipes)} recipe(s) found")

        # Display recipes
        for recipe in recipes:
            display_recipe_card(recipe, show_details_button=True)

    except Exception as e:
        st.error(f"Error loading recipes: {str(e)}")


def show_recipe_details(recipe_id: int):
    """Display detailed view of a specific recipe."""
    if 'recipes_client' not in st.session_state:
        st.session_state.recipes_client = RecipesClient()
        if hasattr(st.session_state, 'access_token'):
            st.session_state.recipes_client.set_tokens(
                st.session_state.access_token,
                getattr(st.session_state, 'refresh_token', None)
            )

    try:
        # Load recipe details
        with st.spinner("Loading recipe..."):
            recipe = st.session_state.recipes_client.get_recipe_with_details(recipe_id)

        # Back button
        if st.button("← Back to Recipe List"):
            if 'selected_recipe_id' in st.session_state:
                del st.session_state.selected_recipe_id
            st.rerun()

        # Recipe header
        st.title(recipe.get("title", "Unknown Recipe"))

        if recipe.get("description"):
            st.markdown(f"*{recipe['description']}*")

        # Recipe metadata
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if recipe.get("cuisine_type"):
                st.info(f"🍽️ {recipe['cuisine_type'].title()}")

        with col2:
            if recipe.get("meal_type"):
                st.info(f"🕐 {recipe['meal_type'].title()}")

        with col3:
            difficulty = recipe.get("difficulty", "medium")
            difficulty_icons = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
            icon = difficulty_icons.get(difficulty.lower(), "🟡")
            st.info(f"{icon} {difficulty.title()}")

        with col4:
            if recipe.get("servings"):
                st.info(f"👥 {recipe['servings']} servings")

        # Time information
        if any([recipe.get("prep_time_minutes"), recipe.get("cook_time_minutes"), recipe.get("total_time_minutes")]):
            time_cols = st.columns(3)

            if recipe.get("prep_time_minutes"):
                time_cols[0].metric("⏱️ Prep Time", f"{recipe['prep_time_minutes']} min")

            if recipe.get("cook_time_minutes"):
                time_cols[1].metric("🔥 Cook Time", f"{recipe['cook_time_minutes']} min")

            if recipe.get("total_time_minutes"):
                time_cols[2].metric("⏰ Total Time", f"{recipe['total_time_minutes']} min")

        # Tags
        if recipe.get("tags"):
            tags_str = " ".join([f"#{tag}" for tag in recipe["tags"]])
            st.markdown(f"🏷️ **Tags:** {tags_str}")

        st.divider()

        # Main content tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🥘 Ingredients",
            "👩‍🍳 Instructions",
            "📊 Nutrition",
            "⭐ Reviews",
            "🍳 Cook"
        ])

        with tab1:
            ingredients = recipe.get("ingredients", [])
            display_recipe_ingredients(ingredients)

        with tab2:
            steps = recipe.get("steps", [])
            display_recipe_steps(steps)

        with tab3:
            nutrition = recipe.get("nutrition")
            display_recipe_nutrition(nutrition)

        with tab4:
            # Load reviews and rating summary
            try:
                reviews = st.session_state.recipes_client.get_recipe_reviews(recipe_id)
                rating_summary = st.session_state.recipes_client.get_recipe_rating_summary(recipe_id)
                display_recipe_reviews(reviews, rating_summary)

                # Review form (if user is logged in)
                if hasattr(st.session_state, 'current_user'):
                    user_id = st.session_state.current_user.get('id')
                    if user_id:
                        review_data = create_recipe_review_form(recipe_id, user_id)
                        if review_data:
                            try:
                                st.session_state.recipes_client.create_recipe_review(
                                    recipe_id, user_id, review_data
                                )
                                st.success("Review added successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error adding review: {str(e)}")

            except Exception as e:
                st.error(f"Error loading reviews: {str(e)}")

        with tab5:
            # Cook recipe functionality
            if hasattr(st.session_state, 'current_user') and hasattr(st.session_state, 'selected_kitchen_id'):
                kitchen_id = st.session_state.selected_kitchen_id
                recipe_title = recipe.get("title", "Recipe")

                if display_cook_recipe_button(recipe_id, kitchen_id, recipe_title):
                    try:
                        with st.spinner("Cooking recipe..."):
                            result = st.session_state.recipes_client.cook_recipe(recipe_id, kitchen_id)

                        if result.get("success"):
                            st.success(f"🎉 {result.get('message', 'Recipe cooked successfully!')}")

                            updated_items = result.get("updated_inventory_items", [])
                            if updated_items:
                                st.info(f"📦 {len(updated_items)} inventory items were updated.")
                        else:
                            st.error("Unexpected error while cooking recipe.")

                    except Exception as e:
                        error_msg = str(e)
                        if "insufficient ingredients" in error_msg.lower():
                            st.error("❌ **Not enough ingredients available!**")
                            st.info("Check your kitchen inventory or buy missing ingredients.")
                        else:
                            st.error(f"Error cooking recipe: {error_msg}")
            else:
                st.warning("⚠️ You must be logged in and have a kitchen selected to cook recipes.")

    except Exception as e:
        st.error(f"Error loading recipe: {str(e)}")
        if st.button("← Back to Recipe List"):
            if 'selected_recipe_id' in st.session_state:
                del st.session_state.selected_recipe_id
            st.rerun()


def show_recipes():
    """Main recipe page controller."""
    # Check if a specific recipe is selected
    if hasattr(st.session_state, 'selected_recipe_id'):
        show_recipe_details(st.session_state.selected_recipe_id)
    else:
        show_recipe_list()


if __name__ == "__main__":
    show_recipes()