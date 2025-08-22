"""Recipe-related UI components for Streamlit."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st


def display_recipe_card(recipe: dict[str, Any], show_details_button: bool = True) -> None:
    """Display a recipe card with basic information."""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            # Title and basic info
            st.subheader(recipe.get("title", "Unknown Recipe"))
            if recipe.get("description"):
                st.write(recipe["description"])

            # Tags
            if recipe.get("tags"):
                tags_str = ", ".join([f"#{tag}" for tag in recipe["tags"]])
                st.caption(f"🏷️ {tags_str}")

        with col2:
            # Recipe metadata
            if recipe.get("cuisine_type"):
                st.write(f"🍽️ **Cuisine:** {recipe['cuisine_type'].title()}")

            if recipe.get("meal_type"):
                st.write(f"🕐 **Meal Type:** {recipe['meal_type'].title()}")

            difficulty_icons = {
                "easy": "🟢",
                "medium": "🟡",
                "hard": "🔴"
            }
            difficulty = recipe.get("difficulty", "medium")
            icon = difficulty_icons.get(difficulty.lower(), "🟡")
            st.write(f"{icon} **Difficulty:** {difficulty.title()}")

            if recipe.get("servings"):
                st.write(f"👥 **Servings:** {recipe['servings']}")

        with col3:
            # Time information
            if recipe.get("prep_time_minutes"):
                st.metric("Prep Time", f"{recipe['prep_time_minutes']} min")

            if recipe.get("cook_time_minutes"):
                st.metric("Cook Time", f"{recipe['cook_time_minutes']} min")

            if recipe.get("total_time_minutes"):
                st.metric("Total Time", f"{recipe['total_time_minutes']} min")

        # AI generated indicator
        if recipe.get("is_ai_generated", False):
            st.info("🤖 This recipe was AI-generated")

        # Details button
        if show_details_button:
            if st.button("View Details", key=f"details_{recipe.get('id')}"):
                st.session_state.selected_recipe_id = recipe["id"]
                st.rerun()

        st.divider()


def display_recipe_ingredients(ingredients: list[dict[str, Any]]) -> None:
    """Display recipe ingredients in a formatted list."""
    st.subheader("🥘 Ingredients")

    if not ingredients:
        st.info("No ingredients found.")
        return

    for ingredient in ingredients:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(f"• **{ingredient.get('food_item_name', 'Unknown')}**")

        with col2:
            amount = ingredient.get('display_amount', 0)
            unit = ingredient.get('display_unit', '')
            st.write(f"{amount} {unit}")


def display_recipe_steps(steps: list[dict[str, Any]]) -> None:
    """Display recipe steps in a numbered list."""
    st.subheader("👩‍🍳 Instructions")

    if not steps:
        st.info("No instructions found.")
        return

    # Sort steps by step_number
    sorted_steps = sorted(steps, key=lambda x: x.get('step_number', 0))

    for step in sorted_steps:
        step_num = step.get('step_number', 1)
        instruction = step.get('instruction', '')

        with st.container():
            st.write(f"**Step {step_num}:**")
            st.write(instruction)
            st.write("")


def display_recipe_nutrition(nutrition: dict[str, Any] | None) -> None:
    """Display recipe nutrition information."""
    if not nutrition:
        st.info("No nutrition information available.")
        return

    st.subheader("📊 Nutrition Facts")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        kcal = nutrition.get('kcal')
        if kcal:
            st.metric("Calories", f"{kcal:.0f} kcal")

    with col2:
        protein = nutrition.get('protein_g')
        if protein:
            st.metric("Protein", f"{protein:.1f}g")

    with col3:
        carbs = nutrition.get('carbs_g')
        if carbs:
            st.metric("Carbs", f"{carbs:.1f}g")

    with col4:
        fat = nutrition.get('fat_g')
        if fat:
            st.metric("Fat", f"{fat:.1f}g")

    if nutrition.get('fiber_g'):
        st.write(f"**Fiber:** {nutrition['fiber_g']:.1f}g")

    source = nutrition.get('source', 'manual')
    st.caption(f"Source: {source}")


def display_recipe_reviews(reviews: list[dict[str, Any]], rating_summary: dict[str, Any] | None = None) -> None:
    """Display recipe reviews and rating summary."""
    st.subheader("⭐ Reviews")

    if rating_summary:
        col1, col2 = st.columns([1, 2])

        with col1:
            avg_rating = rating_summary.get('average_rating', 0)
            total_reviews = rating_summary.get('total_reviews', 0)

            st.metric(
                "Average Rating",
                f"{avg_rating:.1f}/5.0",
                f"({total_reviews} reviews)"
            )

        with col2:
            # Rating distribution
            distribution = rating_summary.get('rating_distribution', {})
            for rating in range(5, 0, -1):
                count = distribution.get(str(rating), 0)
                percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
                st.write(f"{'⭐' * rating} {count} ({percentage:.1f}%)")

    if not reviews:
        st.info("No reviews available.")
        return

    st.write("**Individual Reviews:**")
    for review in reviews:
        with st.container():
            col1, col2 = st.columns([1, 4])

            with col1:
                rating = review.get('rating', 0)
                st.write("⭐" * rating)

                # User info
                user = review.get('user', {})
                user_name = user.get('name', 'Anonymous User')
                st.caption(user_name)

            with col2:
                comment = review.get('comment')
                if comment:
                    st.write(comment)

                # Date
                created_at = review.get('created_at')
                if created_at:
                    try:
                        date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        st.caption(f"Created on {date.strftime('%m/%d/%Y')}")
                    except:
                        pass

            st.divider()


def create_recipe_review_form(recipe_id: int, user_id: int) -> dict[str, Any] | None:
    """Create a form for recipe review submission."""
    st.subheader("💬 Add Review")

    with st.form(f"review_form_{recipe_id}"):
        rating = st.selectbox(
            "Rating",
            options=[1, 2, 3, 4, 5],
            index=4,
            format_func=lambda x: "⭐" * x
        )

        comment = st.text_area(
            "Comment (optional)",
            placeholder="Share your thoughts about this recipe..."
        )

        submitted = st.form_submit_button("Submit Review")

        if submitted:
            review_data = {
                "rating": rating,
                "comment": comment if comment.strip() else None
            }
            return review_data

    return None


def display_recipe_filter_sidebar() -> dict[str, Any]:
    """Display recipe filter options in sidebar."""
    st.sidebar.header("🔍 Recipe Filters")

    filters
