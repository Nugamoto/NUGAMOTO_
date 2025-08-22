"""AI Recipe generation page for NUGAMOTO frontend."""

from __future__ import annotations

import os
import sys
from typing import Any

import streamlit as st

# Add frontend to path for runtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Direct imports for IDE resolution (consistent with other working pages)
try:
    from clients import AIRecipesClient, RecipesClient, APIException
    from components.recipe_components import (
        display_ai_recipe_generation_form,
        display_recipe_ingredients,
        display_recipe_steps,
        display_recipe_nutrition,
    )
except ImportError:
    from frontend.clients import AIRecipesClient, RecipesClient, APIException
    from frontend.components.recipe_components import (
        display_ai_recipe_generation_form,
        display_recipe_ingredients,
        display_recipe_steps,
        display_recipe_nutrition,
    )


def _ensure_clients() -> tuple[AIRecipesClient, RecipesClient]:
    """Ensure API clients exist and carry tokens from session."""
    if "ai_recipes_client" not in st.session_state:
        st.session_state.ai_recipes_client = AIRecipesClient()
    if "recipes_client" not in st.session_state:
        st.session_state.recipes_client = RecipesClient()

    # Apply tokens if available
    if getattr(st.session_state, "auth_access_token", None):
        access = st.session_state.auth_access_token
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        st.session_state.ai_recipes_client.set_tokens(access, refresh)
        st.session_state.recipes_client.set_tokens(access, refresh)

    return st.session_state.ai_recipes_client, st.session_state.recipes_client


def show_ai_recipe_generator() -> None:
    """Render the AI recipe generation form and handle submission."""
    st.title("🤖 AI Recipe Generator")
    st.markdown("Let our AI create a personalized recipe based on your preferences and inventory.")

    ai_client, _ = _ensure_clients()

    # Ensure user/kitchen context
    current_user = getattr(st.session_state, "current_user", None)
    kitchen_id = getattr(st.session_state, "selected_kitchen_id", None)
    if not current_user or not kitchen_id:
        st.warning("⚠️ You must be logged in and have a kitchen selected to generate AI recipes.")
        return

    # Minimal change: fall back to '1' if user id is missing (MVP-friendly)
    try:
        user_id = int(current_user.get("id") or 1)
    except Exception:
        user_id = 1

    # Show form and submit
    request_payload = display_ai_recipe_generation_form()
    if not request_payload:
        return

    try:
        with st.spinner("🤖 Generating recipe..."):
            ai_result: dict[str, Any] = ai_client.generate_recipe(
                user_id=user_id,
                kitchen_id=int(kitchen_id),
                recipe_request=request_payload,
            )
        st.session_state.ai_generated_recipe = ai_result
        st.success("🎉 Recipe generated successfully!")
        st.rerun()
    except APIException as e:
        st.error(f"API error while generating recipe: {e.message}")
    except Exception as e:
        st.error(f"Error generating recipe: {str(e)}")


def display_generated_recipe(ai_result: dict[str, Any], user_id: int) -> None:
    """Render the AI-generated recipe and provide save action."""
    st.divider()
    st.header("🤖 Generated Recipe")

    recipe_data = ai_result.get("recipe") or {}
    ai_output = ai_result.get("ai_output") or {}
    ai_output_id = ai_output.get("id")

    if not recipe_data:
        st.error("Error: Recipe data not available.")
        return

    # Header
    st.subheader(recipe_data.get("title", "Unknown Recipe"))
    if recipe_data.get("description"):
        st.markdown(f"*{recipe_data['description']}*")

    meta_cols = st.columns(4)
    if recipe_data.get("cuisine_type"):
        meta_cols[0].info(f"🍽️ {str(recipe_data['cuisine_type']).title()}")
    if recipe_data.get("meal_type"):
        meta_cols[1].info(f"🕐 {str(recipe_data['meal_type']).title()}")
    difficulty = str(recipe_data.get("difficulty", "medium")).lower()
    icon = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(difficulty, "🟡")
    meta_cols[2].info(f"{icon} {difficulty.title()}")
    if recipe_data.get("servings"):
        meta_cols[3].info(f"👥 {recipe_data['servings']} servings")

    time_cols = st.columns(3)
    if recipe_data.get("prep_time_minutes"):
        time_cols[0].metric("⏱️ Prep Time", f"{recipe_data['prep_time_minutes']} min")
    if recipe_data.get("cook_time_minutes"):
        time_cols[1].metric("🔥 Cook Time", f"{recipe_data['cook_time_minutes']} min")
    if recipe_data.get("total_time_minutes"):
        time_cols[2].metric("⏰ Total Time", f"{recipe_data['total_time_minutes']} min")

    if recipe_data.get("tags"):
        st.markdown("🏷️ " + " ".join(f"#{t}" for t in recipe_data["tags"]))

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🥘 Ingredients", "👩‍🍳 Instructions", "📊 Nutrition"])
    with tab1:
        display_recipe_ingredients(recipe_data.get("ingredients", []))
    with tab2:
        display_recipe_steps(recipe_data.get("steps", []))
    with tab3:
        display_recipe_nutrition(recipe_data.get("nutrition"))

    st.divider()
    st.subheader("💾 Save Recipe")
    st.info("Like the generated recipe? Save it to your collection!")

    col1, col2, _ = st.columns([1, 1, 3])
    if col1.button("✅ Save Recipe", type="primary", disabled=not ai_output_id):
        save_ai_recipe(ai_output_id=int(ai_output_id), user_id=int(user_id))
    if col2.button("🔄 Generate Another"):
        if "ai_generated_recipe" in st.session_state:
            del st.session_state.ai_generated_recipe
        st.rerun()


def save_ai_recipe(ai_output_id: int, user_id: int) -> None:
    """Convert and persist the AI recipe; then mark saved."""
    ai_client, recipes_client = _ensure_clients()

    try:
        with st.spinner("Preparing recipe for saving..."):
            recipe_create = ai_client.convert_ai_recipe_to_create(
                ai_output_id=ai_output_id,
                user_id=user_id,
            )

        with st.spinner("Saving recipe..."):
            saved_recipe = recipes_client.create_recipe(recipe_create)
            recipe_id = int(saved_recipe.get("id") or 0)

        if recipe_id:
            ai_client.mark_ai_recipe_as_saved(
                ai_output_id=ai_output_id,
                recipe_id=recipe_id,
                user_id=user_id,
            )
            st.success("🎉 Recipe saved successfully!")
            if st.button("📖 View Saved Recipe"):
                st.session_state.selected_recipe_id = recipe_id
                if "ai_generated_recipe" in st.session_state:
                    del st.session_state.ai_generated_recipe
                st.switch_page("pages/recipes.py")
        else:
            st.error("Error: Missing recipe id after save.")

    except APIException as e:
        st.error(f"API error while saving recipe: {e.message}")
    except Exception as e:
        st.error(f"Error saving recipe: {str(e)}")


def show_recent_ai_recipes() -> None:
    """List recently saved AI-generated recipes."""
    st.header("📚 AI Recipes")

    _, recipes_client = _ensure_clients()

    try:
        with st.spinner("Loading AI-generated recipes..."):
            recipes = recipes_client.get_ai_generated_recipes(limit=20)

        if not recipes:
            st.info("No AI-generated recipes yet. Create your first recipe!")
            return

        st.success(f"Found {len(recipes)} AI-generated recipe(s).")

        for r in recipes:
            with st.container():
                cols = st.columns([3, 2, 1])
                with cols[0]:
                    st.subheader(r.get("title", "Unknown Recipe"))
                    if r.get("description"):
                        st.write(r["description"])
                with cols[1]:
                    difficulty = str(r.get("difficulty", "medium")).lower()
                    icon = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(difficulty, "🟡")
                    st.write(f"{icon} Difficulty: {difficulty.title()}")
                    if r.get("cuisine_type"):
                        st.write(f"🍽️ Cuisine: {str(r['cuisine_type']).title()}")
                with cols[2]:
                    if st.button("Details", key=f"ai_recipe_{r.get('id')}"):
                        st.session_state.selected_recipe_id = r["id"]
                        st.switch_page("pages/recipes.py")
                st.divider()

    except APIException as e:
        st.error(f"API error while loading AI recipes: {e.message}")
    except Exception as e:
        st.error(f"Error loading AI recipes: {str(e)}")


def show_ai_recipes() -> None:
    """Main AI recipes page controller."""
    tab1, tab2 = st.tabs(["🤖 Generator", "📚 AI Recipes"])
    with tab1:
        show_ai_recipe_generator()
    with tab2:
        show_recent_ai_recipes()


if __name__ == "__main__":
    show_ai_recipes()