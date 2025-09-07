"""Recipe-related UI components for Streamlit."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st


def display_recipe_card(recipe: dict[str, Any], show_details_button: bool = True) -> None:
    """Render a compact recipe card with common metadata."""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.subheader(recipe.get("title", "Unknown Recipe"))
            if recipe.get("description"):
                st.write(recipe["description"])
            if recipe.get("tags"):
                tags_str = ", ".join(f"#{t}" for t in recipe["tags"])
                st.caption(f"🏷️ {tags_str}")

        with col2:
            if recipe.get("cuisine_type"):
                st.write(f"🍽️  Cuisine: {str(recipe['cuisine_type']).title()}")
            if recipe.get("meal_type"):
                st.write(f"🕐  Meal: {str(recipe['meal_type']).title()}")
            difficulty = str(recipe.get("difficulty", "medium")).lower()
            icon = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(difficulty, "🟡")
            st.write(f"{icon} Difficulty: {difficulty.title()}")
            if recipe.get("servings"):
                st.write(f"👥 Servings: {recipe['servings']}")

        with col3:
            if recipe.get("prep_time_minutes"):
                st.metric("Prep", f"{recipe['prep_time_minutes']} min")
            if recipe.get("cook_time_minutes"):
                st.metric("Cook", f"{recipe['cook_time_minutes']} min")
            if recipe.get("total_time_minutes"):
                st.metric("Total", f"{recipe['total_time_minutes']} min")

        if recipe.get("is_ai_generated"):
            st.info("🤖 AI-generated")

        if show_details_button:
            if st.button("View Details", key=f"details_{recipe.get('id')}"):
                st.session_state.selected_recipe_id = recipe["id"]
                st.rerun()

        st.divider()


def display_recipe_ingredients(ingredients: list[dict[str, Any]]) -> None:
    """Render ingredient list with display amount and unit."""
    st.subheader("🥘 Ingredients")

    if not ingredients:
        st.info("No ingredients found.")
        return

    for ing in ingredients:
        left, right = st.columns([3, 1])
        with left:
            st.write(f"• {ing.get('food_item_name', 'Unknown')}")
        with right:
            amount = ing.get("display_amount")
            unit = ing.get("display_unit")
            if amount is not None and unit:
                st.write(f"{amount} {unit}")
            elif amount is not None:
                st.write(str(amount))
            else:
                st.write("-")


def display_recipe_steps(steps: list[dict[str, Any]]) -> None:
    """Render step-by-step instructions."""
    st.subheader("👩‍🍳 Instructions")

    if not steps:
        st.info("No instructions found.")
        return

    for step in sorted(steps, key=lambda s: s.get("step_number", 0)):
        number = step.get("step_number", 1)
        instruction = step.get("instruction", "").strip()
        if not instruction:
            continue
        st.markdown(f"**Step {number}**")
        st.write(instruction)
        st.write("")


def display_recipe_nutrition(nutrition: dict[str, Any] | None) -> None:
    """Render compact nutrition metrics."""
    st.subheader("📊 Nutrition")

    if not nutrition:
        st.info("No nutrition information available.")
        return

    cols = st.columns(4)
    kcal = nutrition.get("kcal")
    protein = nutrition.get("protein_g")
    carbs = nutrition.get("carbs_g")
    fat = nutrition.get("fat_g")

    if kcal is not None:
        cols[0].metric("Calories", f"{kcal:.0f} kcal")
    if protein is not None:
        cols[1].metric("Protein", f"{protein:.1f} g")
    if carbs is not None:
        cols[2].metric("Carbs", f"{carbs:.1f} g")
    if fat is not None:
        cols[3].metric("Fat", f"{fat:.1f} g")

    fiber = nutrition.get("fiber_g")
    if fiber is not None:
        st.caption(f"Fiber: {fiber:.1f} g")

    source = nutrition.get("source") or "manual"
    st.caption(f"Source: {source}")


def display_recipe_reviews(reviews: list[dict[str, Any]], rating_summary: dict[str, Any] | None = None) -> None:
    """Render rating summary and individual reviews."""
    st.subheader("⭐ Reviews")

    if rating_summary:
        left, right = st.columns([1, 2])
        with left:
            avg = rating_summary.get("average_rating") or 0
            total = rating_summary.get("total_reviews") or 0
            left.metric("Average Rating", f"{avg:.1f}/5.0", f"({total} reviews)")
        with right:
            dist = rating_summary.get("rating_distribution") or {}
            # distribution keys may be str or int; normalize to int
            normalized = {int(k): v for k, v in dist.items()}
            total_reviews = rating_summary.get("total_reviews") or 0
            for stars in range(5, 0, -1):
                cnt = normalized.get(stars, 0)
                pct = (cnt / total_reviews * 100) if total_reviews > 0 else 0.0
                right.write(f"{'⭐' * stars} {cnt} ({pct:.1f}%)")

    if not reviews:
        st.info("No reviews available.")
        return

    for r in reviews:
        row1, row2 = st.columns([1, 4])
        with row1:
            st.write("⭐" * int(r.get("rating", 0)))
            user = r.get("user") or {}
            st.caption(user.get("name", "Anonymous"))
        with row2:
            comment = (r.get("comment") or "").strip()
            if comment:
                st.write(comment)
            created_at = r.get("created_at")
            if created_at:
                try:
                    dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                    st.caption(f"Created on {dt.strftime('%m/%d/%Y')}")
                except Exception:
                    pass
        st.divider()


def create_recipe_review_form(recipe_id: int, user_id: int) -> dict[str, Any] | None:
    """Render a review form; return payload on submit, otherwise None."""
    st.subheader("💬 Add Review")

    with st.form(f"review_form_{recipe_id}_{user_id}"):
        rating = st.selectbox("Rating", options=[1, 2, 3, 4, 5], index=4, format_func=lambda x: "⭐" * x)
        comment = st.text_area("Comment (optional)", placeholder="Share your thoughts...")
        submitted = st.form_submit_button("Submit Review", type="primary")

        if submitted:
            return {
                "rating": rating,
                "comment": comment.strip() or None,
            }

    return None


def display_recipe_filter_sidebar() -> dict[str, Any]:
    """Render sidebar filters; return dict of query params for the API."""
    st.sidebar.header("🔍 Recipe Filters")

    filters: dict[str, Any] = {}

    title_contains = st.sidebar.text_input("Title contains", placeholder="Search recipes...")
    if title_contains.strip():
        filters["title_contains"] = title_contains.strip()

    recipe_type = st.sidebar.selectbox("Recipe Type", ["All", "AI-generated", "Manual"], index=0)
    if recipe_type == "AI-generated":
        filters["is_ai_generated"] = True
    elif recipe_type == "Manual":
        filters["is_ai_generated"] = False

    difficulty = st.sidebar.selectbox("Difficulty", ["All", "easy", "medium", "hard"], index=0)
    if difficulty != "All":
        filters["difficulty"] = difficulty

    if st.sidebar.checkbox("Only with nutrition info"):
        filters["has_nutrition"] = True

    max_kcal = st.sidebar.number_input("Max. Calories", min_value=0, max_value=2000, value=0, step=50)
    if max_kcal > 0:
        filters["max_kcal"] = max_kcal

    min_protein = st.sidebar.number_input("Min. Protein (g)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    if min_protein > 0:
        filters["min_protein_g"] = float(min_protein)

    tags_input = st.sidebar.text_input("Tags (comma-separated)", placeholder="e.g. vegetarian, quick")
    if tags_input.strip():
        tags = [t.strip() for t in tags_input.split(",") if t.strip()]
        if tags:
            filters["tags_contains"] = tags

    return filters


def display_cook_recipe_button(recipe_id: int, kitchen_id: int, recipe_title: str) -> bool:
    """Render a 'Cook Recipe' action; return True when clicked."""
    st.subheader("🍳 Cook Recipe")
    st.info("Cooking this recipe will consume ingredients from your kitchen inventory.")
    return st.button(f"🍳 Cook '{recipe_title}'", type="primary")


def display_ai_recipe_generation_form() -> dict[str, Any] | None:
    """Render AI recipe generation form; return request payload on submit."""
    st.subheader("🤖 Generate AI Recipe")

    with st.form("ai_recipe_form"):
        left, right = st.columns(2)

        with left:
            cuisine_type = st.text_input("Cuisine Type", placeholder="e.g. italian, asian, mexican")
            meal_type = st.selectbox(
                "Meal Type",
                options=["", "breakfast", "lunch", "dinner", "snack"],
                format_func=lambda x: {
                    "": "Any",
                    "breakfast": "Breakfast",
                    "lunch": "Lunch",
                    "dinner": "Dinner",
                    "snack": "Snack",
                }.get(x, x),
            )
            difficulty_level = st.selectbox(
                "Difficulty",
                options=["", "easy", "medium", "hard"],
                format_func=lambda x: {"": "Any", "easy": "Easy", "medium": "Medium", "hard": "Hard"}.get(x, x),
            )
            servings = st.number_input("Servings", min_value=1, max_value=20, value=2, step=1)

        with right:
            max_prep_time = st.number_input("Max. Prep Time (minutes)", min_value=0, max_value=480, value=0, step=5)
            max_cook_time = st.number_input("Max. Cook Time (minutes)", min_value=0, max_value=480, value=0, step=5)
            dietary_restrictions = st.text_input(
                "Dietary Restrictions",
                placeholder="e.g. vegetarian, vegan, gluten-free (comma-separated)",
            )
            exclude_ingredients = st.text_input(
                "Exclude Ingredients",
                placeholder="e.g. nuts, dairy (comma-separated)",
            )

        special_requests = st.text_area("Special Requests", placeholder="Describe what kind of recipe you want...")

        with st.expander("Advanced Options"):
            prioritize_expiring = st.checkbox(
                "Prioritize expiring ingredients",
                value=True,
                help="Prefer ingredients that expire soon.",
            )
            prefer_available = st.checkbox(
                "Prefer available ingredients",
                value=True,
                help="Prefer ingredients available in kitchen inventory.",
            )
            required_appliances = st.text_input("Required Appliances", placeholder="e.g. oven, microwave (comma-separated)")
            avoid_appliances = st.text_input("Avoid Appliances", placeholder="e.g. deep fryer, grill (comma-separated)")

        submitted = st.form_submit_button("🤖 Generate Recipe", type="primary")

        if not submitted:
            return None

        payload: dict[str, Any] = {}

        if cuisine_type.strip():
            payload["cuisine_type"] = cuisine_type.strip()
        if meal_type:
            payload["meal_type"] = meal_type
        if difficulty_level:
            payload["difficulty_level"] = difficulty_level
        if max_prep_time > 0:
            payload["max_prep_time"] = int(max_prep_time)
        if max_cook_time > 0:
            payload["max_cook_time"] = int(max_cook_time)
        if servings:
            payload["servings"] = int(servings)

        if dietary_restrictions.strip():
            payload["dietary_restrictions"] = [x.strip() for x in dietary_restrictions.split(",") if x.strip()]
        if exclude_ingredients.strip():
            payload["exclude_ingredients"] = [x.strip() for x in exclude_ingredients.split(",") if x.strip()]

        if special_requests.strip():
            payload["special_requests"] = special_requests.strip()

        payload["prioritize_expiring"] = bool(prioritize_expiring)
        payload["prefer_available_ingredients"] = bool(prefer_available)

        if required_appliances.strip():
            payload["required_appliances"] = [x.strip() for x in required_appliances.split(",") if x.strip()]
        if avoid_appliances.strip():
            payload["avoid_appliances"] = [x.strip() for x in avoid_appliances.split(",") if x.strip()]

        return payload