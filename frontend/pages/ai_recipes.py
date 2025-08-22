"""AI Recipe generation page for NUGAMOTO frontend."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import streamlit as st

# Add frontend to path for runtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
    if "ai_recipes_client" not in st.session_state:
        st.session_state.ai_recipes_client = AIRecipesClient()
    if "recipes_client" not in st.session_state:
        st.session_state.recipes_client = RecipesClient()
    if getattr(st.session_state, "auth_access_token", None):
        access = st.session_state.auth_access_token
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        st.session_state.ai_recipes_client.set_tokens(access, refresh)
        st.session_state.recipes_client.set_tokens(access, refresh)
    return st.session_state.ai_recipes_client, st.session_state.recipes_client


def _require_user() -> int | None:
    cu = st.session_state.get("current_user")
    if not isinstance(cu, dict) or cu.get("id") is None:
        st.warning("User context missing. Please login again.")
        st.switch_page("pages/login.py")
        return None
    return int(cu["id"])


def _parse_recipe_from_raw_output(raw_output: str) -> dict[str, Any]:
    try:
        return json.loads(raw_output)
    except Exception:
        return {}


def _preview_from_output_row(output_row: dict[str, Any]) -> None:
    """Load a single AIModelOutput row into the standard preview flow and rerun."""
    ai_output_id = output_row.get("id")
    raw = output_row.get("raw_output", "")
    parsed_recipe = _parse_recipe_from_raw_output(raw) or {}

    # Shape compatible with display_generated_recipe
    ai_result = {"recipe": parsed_recipe, "ai_output": {"id": ai_output_id}}
    st.session_state.ai_generated_recipe = ai_result
    st.rerun()


# -------------------------- Preview Enrichment -------------------------- #
def _ensure_preview_caches() -> None:
    """Initialize caches used to resolve names for preview."""
    st.session_state.setdefault("_ai_preview_food_names", {})  # {food_item_id: name}
    st.session_state.setdefault("_ai_preview_unit_names", {})  # {unit_id: name}


def _resolve_food_name(food_item_id: int, client: AIRecipesClient) -> str:
    """Resolve food item name by ID with caching. Fallback to '#<id>'."""
    cache: dict[int, str] = st.session_state._ai_preview_food_names
    if food_item_id in cache:
        return cache[food_item_id]
    try:
        # Typical REST path in this project
        data = client.get(f"/v1/food-items/{food_item_id}")
        name = str(data.get("name") or f"#{food_item_id}")
    except Exception:
        name = f"#{food_item_id}"
    cache[food_item_id] = name
    return name


def _resolve_unit_name(unit_id: int, client: AIRecipesClient) -> str:
    """Resolve unit name by ID with caching. Fallback to '#<id>'."""
    cache: dict[int, str] = st.session_state._ai_preview_unit_names
    if unit_id in cache:
        return cache[unit_id]
    try:
        data = client.get(f"/v1/units/{unit_id}")
        name = str(data.get("name") or f"#{unit_id}")
    except Exception:
        name = f"#{unit_id}"
    cache[unit_id] = name
    return name


def _normalize_ingredients_for_preview(
        raw_ingredients: list[dict[str, Any]] | None,
        client: AIRecipesClient
) -> list[dict[str, Any]]:
    """Transform AI raw_output ingredients to the shape expected by display_recipe_ingredients."""
    _ensure_preview_caches()
    if not raw_ingredients:
        return []

    normalized: list[dict[str, Any]] = []
    for ing in raw_ingredients:
        # AI raw_output typically includes: food_item_id, original_unit_id, original_amount
        food_item_id = ing.get("food_item_id")
        original_amount = ing.get("original_amount")
        original_unit_id = ing.get("original_unit_id")

        # Resolve names
        food_name = _resolve_food_name(int(food_item_id), client) if food_item_id is not None else "Unknown"
        unit_name = _resolve_unit_name(int(original_unit_id), client) if original_unit_id is not None else None

        # display_* fields are what our UI component expects
        display_amount = original_amount if isinstance(original_amount, (int, float)) else None
        display_unit = unit_name

        normalized.append(
            {
                "food_item_name": food_name or "Unknown",
                "display_amount": display_amount,
                "display_unit": display_unit,
            }
        )

    return normalized


# ------------------------------------------------------------------------ #


def show_ai_recipe_generator() -> None:
    """Render the AI recipe generation form and handle submission."""
    st.title("🤖 AI Recipe Generator")
    st.markdown("Let our AI create a personalized recipe based on your preferences and inventory.")

    ai_client, _ = _ensure_clients()

    # Require user
    user_id = _require_user()
    if user_id is None:
        return

    # Kitchen inline selection (only if not set)
    kitchen_id = st.session_state.get("selected_kitchen_id")
    if not kitchen_id:
        st.info("Please select a kitchen to continue.")
        col1, col2 = st.columns([2, 1])
        with col1:
            chosen_id = st.number_input("Kitchen ID", min_value=1, step=1, value=1, key="__ai_kitchen_pick__")
        with col2:
            if st.button("Use this Kitchen", type="primary"):
                st.session_state.selected_kitchen_id = int(chosen_id)
                st.session_state.selected_kitchen_name = f"Kitchen {int(chosen_id)}"
                st.success("Kitchen selected.")
                st.rerun()
        return
    kitchen_id = int(kitchen_id)

    # Show form and submit
    request_payload = display_ai_recipe_generation_form()
    if not request_payload:
        return

    try:
        with st.spinner("🤖 Generating recipe..."):
            ai_result: dict[str, Any] = ai_client.generate_recipe(
                user_id=user_id,
                kitchen_id=kitchen_id,
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
    st.subheader("Preview")
    ai_client, _ = _ensure_clients()

    recipe_data = ai_result.get("recipe") or {}
    ai_output = ai_result.get("ai_output") or {}
    ai_output_id = ai_output.get("id")

    if not recipe_data:
        st.error("Error: Recipe data not available.")
        return

    # Header
    st.markdown(f"### {recipe_data.get('title', 'Unknown Recipe')}")
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

    # Normalize ingredients before rendering to avoid "Unknown"
    normalized_ingredients = _normalize_ingredients_for_preview(recipe_data.get("ingredients"), ai_client)

    # Tabs: Ingredients, Instructions, Nutrition
    tab1, tab2, tab3 = st.tabs(["🥘 Ingredients", "👩‍🍳 Instructions", "📊 Nutrition"])
    with tab1:
        display_recipe_ingredients(normalized_ingredients)
    with tab2:
        display_recipe_steps(recipe_data.get("steps", []))
    with tab3:
        display_recipe_nutrition(recipe_data.get("nutrition"))

    st.divider()
    st.subheader("Decision")
    st.info("Would you like to add this recipe to your collection?")
    actions = st.columns([1, 1, 4])
    with actions[0]:
        if st.button("✅ Save Recipe", type="primary", disabled=not ai_output_id, key="save_recipe_btn"):
            save_ai_recipe(ai_output_id=int(ai_output_id), user_id=int(user_id))
            return
    with actions[1]:
        if st.button("❌ Close Preview", key="close_preview_btn"):
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
            # Clear preview and open details page
            if "ai_generated_recipe" in st.session_state:
                del st.session_state.ai_generated_recipe
            if st.button("📖 View Saved Recipe", key="view_saved_recipe_btn"):
                st.session_state.selected_recipe_id = recipe_id
                st.switch_page("pages/recipes.py")
        else:
            st.error("Error: Missing recipe id after save.")

    except APIException as e:
        st.error(f"API error while saving recipe: {e.message}")
    except Exception as e:
        st.error(f"Error saving recipe: {str(e)}")


def show_recent_ai_recipes() -> None:
    """List AI recipe drafts: output_type=recipe, target_type=Recipe, status=generated (client-side)."""
    st.header("📚 AI Recipe Drafts (status=generated)")

    ai_client, _ = _ensure_clients()
    user_id = _require_user()
    if user_id is None:
        return

    try:
        with st.spinner("Loading AI recipe drafts..."):
            params = {
                "user_id": user_id,
                "target_type": "Recipe",
                "output_type": "recipe",
                "skip": 0,
                "limit": 50,
            }
            outputs = ai_client.get("/v1/ai/outputs/", params=params)

        # Client-side filter: only show status='generated' and unsaved (target_id is None)
        drafts: list[dict[str, Any]] = []
        for row in outputs or []:
            extra = row.get("extra_data") or {}
            status = extra.get("status")
            if status == "generated" and not row.get("target_id"):
                drafts.append(row)

        if not drafts:
            st.info("No generated AI recipe drafts yet. Create one in the Generator tab.")
            return

        st.caption(f"{len(drafts)} draft(s) found")
        for row in drafts:
            raw = row.get("raw_output", "")
            parsed = _parse_recipe_from_raw_output(raw) or {}
            title = parsed.get("title") or f"Draft #{row.get('id')}"
            description = parsed.get("description") or ""

            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(title)
                if description:
                    st.write(description)
                st.caption(
                    f"Draft ID: {row.get('id')} • "
                    f"Status: {(row.get('extra_data') or {}).get('status', 'generated')}"
                )
            with col2:
                if st.button("Preview", key=f"preview_{row.get('id')}"):
                    _preview_from_output_row(row)

            st.divider()

    except APIException as e:
        st.error("Failed to load AI recipe drafts (AIModelOutputs).")
        st.code(f"Status: {e.status_code}\nMessage: {e.message}")
    except Exception as e:
        st.error(f"Error loading drafts: {str(e)}")


def _show_preview_if_present() -> None:
    """Render a sticky preview panel if a draft/generation is present in session."""
    ai_result = st.session_state.get("ai_generated_recipe")
    if not ai_result:
        return
    user_id = _require_user()
    if user_id is None:
        return

    with st.container():
        st.success("Preview loaded from AI draft")
        display_generated_recipe(ai_result, user_id)
        st.divider()


def show_ai_recipes() -> None:
    """Main AI recipes page controller."""
    # Always render preview first if present (works for both generated and drafts)
    _show_preview_if_present()

    tab1, tab2 = st.tabs(["🤖 Generator", "📚 AI Recipes"])
    with tab1:
        show_ai_recipe_generator()
    with tab2:
        show_recent_ai_recipes()


if __name__ == "__main__":
    show_ai_recipes()