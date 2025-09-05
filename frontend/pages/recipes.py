"""Recipe management page for NUGAMOTO frontend."""

from __future__ import annotations

from typing import Any

import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path
from frontend.utils.layout import render_sidebar

ensure_frontend_on_sys_path(__file__)

from frontend.clients import RecipesClient, APIException
from frontend.components.recipe_components import (
    display_recipe_card,
    display_recipe_ingredients,
    display_recipe_steps,
    display_recipe_nutrition,
    display_recipe_reviews,
    create_recipe_review_form,
    display_recipe_filter_sidebar,
    display_cook_recipe_button,
)


class RecipesPageController:
    def __init__(self) -> None:
        render_sidebar()
        self.client = self._ensure_client()


    @staticmethod
    def _ensure_client() -> RecipesClient:
        if "recipes_client" not in st.session_state:
            st.session_state.recipes_client = RecipesClient()
        if hasattr(st.session_state, "auth_access_token") and st.session_state.auth_access_token:
            st.session_state.recipes_client.set_tokens(
                st.session_state.auth_access_token,
                getattr(st.session_state, "auth_refresh_token", None),
            )
        return st.session_state.recipes_client


    @staticmethod
    def _compute_rating_summary_from_reviews(reviews: list[dict]) -> dict[str, Any]:
        if not reviews:
            return {
                "recipe_id": None,
                "total_reviews": 0,
                "average_rating": 0.0,
                "rating_distribution": {str(i): 0 for i in range(1, 6)},
            }
        total = len(reviews)
        ratings = [int(r.get("rating", 0) or 0) for r in reviews if int(r.get("rating", 0) or 0) in (1, 2, 3, 4, 5)]
        avg = (sum(ratings) / len(ratings)) if ratings else 0.0
        dist: dict[str, int] = {str(i): 0 for i in range(1, 6)}
        for r in ratings:
            dist[str(r)] += 1
        return {"recipe_id": None, "total_reviews": total, "average_rating": float(avg), "rating_distribution": dist}


    def _show_recipe_list(self) -> None:
        st.title("📖 Recipes")
        st.markdown("Discover delicious recipes or create your own!")
        filters = display_recipe_filter_sidebar()
        try:
            with st.spinner("Loading recipes..."):
                recipes = self.client.get_all_recipes(**filters)
            if not recipes:
                st.info("No recipes found. Try different filter criteria or create a new recipe!")
                return
            st.success(f"📚 {len(recipes)} recipe(s) found")
            for recipe in recipes:
                display_recipe_card(recipe)
        except APIException as e:
            st.error(f"API error while loading recipes: {e.message}")
        except Exception as e:
            st.error(f"Error loading recipes: {str(e)}")


    def _show_recipe_details(self, recipe_id: int) -> None:
        try:
            with st.spinner("Loading recipe..."):
                recipe = self.client.get_recipe_with_details(recipe_id)
            if st.button("← Back to Recipe List"):
                if "selected_recipe_id" in st.session_state:
                    del st.session_state.selected_recipe_id
                st.rerun()
            st.title(recipe.get("title", "Unknown Recipe"))
            if recipe.get("description"):
                st.markdown(f"*{recipe['description']}*")
            meta_cols = st.columns(4)
            if recipe.get("cuisine_type"):
                meta_cols[0].info(f"🍽️ {str(recipe['cuisine_type']).title()}")
            if recipe.get("meal_type"):
                meta_cols[1].info(f"🕐 {str(recipe['meal_type']).title()}")
            if recipe.get("difficulty"):
                meta_cols[2].info(f"🎯 {str(recipe['difficulty']).title()}")
            if recipe.get("servings"):
                meta_cols[3].info(f"👥 {recipe['servings']} servings")
            time_cols = st.columns(3)
            if recipe.get("prep_time_minutes"):
                time_cols[0].metric("⏱️ Prep Time", f"{recipe['prep_time_minutes']} min")
            if recipe.get("cook_time_minutes"):
                time_cols[1].metric("🔥 Cook Time", f"{recipe['cook_time_minutes']} min")
            if recipe.get("total_time_minutes"):
                time_cols[2].metric("⏰ Total Time", f"{recipe['total_time_minutes']} min")
            if recipe.get("tags"):
                st.markdown("🏷️ " + " ".join(f"#{t}" for t in recipe["tags"]))
            st.divider()
            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                ["🥘 Ingredients", "👩‍🍳 Instructions", "📊 Nutrition", "⭐ Reviews", "🍳 Cook"]
            )
            with tab1:
                display_recipe_ingredients(recipe.get("ingredients", []))
            with tab2:
                display_recipe_steps(recipe.get("steps", []))
            with tab3:
                display_recipe_nutrition(recipe.get("nutrition"))
            with tab4:
                try:
                    reviews = self.client.get_recipe_reviews(recipe_id)
                    if not reviews:
                        rating_summary = None
                    else:
                        try:
                            rating_summary = self.client.get_recipe_rating_summary(recipe_id)
                        except APIException:
                            rating_summary = self._compute_rating_summary_from_reviews(reviews)
                        except Exception:
                            rating_summary = self._compute_rating_summary_from_reviews(reviews)
                    if rating_summary and "rating_distribution" in rating_summary:
                        rating_summary["rating_distribution"] = {
                            str(k): v for k, v in rating_summary["rating_distribution"].items()
                        }
                    display_recipe_reviews(reviews, rating_summary)
                    current_user = getattr(st.session_state, "current_user", None)
                    if current_user and current_user.get("id"):
                        user_id = int(current_user["id"])
                        review_data = create_recipe_review_form(recipe_id, user_id)
                        if review_data:
                            self.client.create_recipe_review(recipe_id, user_id, review_data)
                            st.success("Review added successfully!")
                            st.rerun()
                except APIException as e:
                    st.error(f"API error loading reviews: {e.message}")
                except Exception as e:
                    st.error(f"Error loading reviews: {str(e)}")
            with tab5:
                current_user = getattr(st.session_state, "current_user", None)
                kitchen_id = getattr(st.session_state, "selected_kitchen_id", None)
                if current_user and kitchen_id:
                    title = recipe.get("title", "Recipe")
                    if display_cook_recipe_button(recipe_id, int(kitchen_id), title):
                        try:
                            with st.spinner("Cooking recipe..."):
                                result = self.client.cook_recipe(recipe_id, int(kitchen_id))
                            if result.get("success"):
                                st.success(result.get("message", "Recipe cooked successfully!"))
                                updated = result.get("updated_inventory_items", [])
                                if updated:
                                    st.info(f"📦 {len(updated)} inventory items were updated.")
                            else:
                                st.error("Unexpected error while cooking recipe.")
                        except APIException as e:
                            st.error(f"API error while cooking recipe: {e.message}")
                        except Exception as e:
                            st.error(f"Error cooking recipe: {str(e)}")
                else:
                    st.warning("You must be logged in and have a kitchen selected to cook recipes.")
        except APIException as e:
            st.error(f"API error while loading recipe: {e.message}")
        except Exception as e:
            st.error(f"Error loading recipe: {str(e)}")
            if st.button("← Back to Recipe List"):
                if "selected_recipe_id" in st.session_state:
                    del st.session_state.selected_recipe_id
                st.rerun()


    def render(self) -> None:
        if hasattr(st.session_state, "selected_recipe_id"):
            self._show_recipe_details(int(st.session_state.selected_recipe_id))
        else:
            self._show_recipe_list()


def main() -> None:
    st.set_page_config(page_title="Recipes - NUGAMOTO")
    RecipesPageController().render()


if __name__ == "__main__":
    main()
