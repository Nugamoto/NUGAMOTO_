# streamlit_app.py
from datetime import datetime
from typing import Dict

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# Configuration
API_BASE_URL = "http://127.0.0.1:8000/v1"


class NugamotoAPI:
    """API client for Nugamoto backend."""


    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url


    def get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make GET request to API."""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API server. Please ensure the FastAPI server is running.")
            return {"error": True}
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")
            return {"error": True}


    def post(self, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make POST request to API."""
        try:
            response = requests.post(f"{self.base_url}{endpoint}", json=data, params=params)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API server.")
            return {"error": True}
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")
            return {"error": True}


    def put(self, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make PUT request to API."""
        try:
            response = requests.put(f"{self.base_url}{endpoint}", json=data, params=params)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API server.")
            return {"error": True}
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")
            return {"error": True}


    def patch(self, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make PATCH request to API."""
        try:
            response = requests.patch(f"{self.base_url}{endpoint}", json=data, params=params)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API server.")
            return {"error": True}
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")
            return {"error": True}


    def delete(self, endpoint: str) -> Dict:
        """Make DELETE request to API."""
        try:
            response = requests.delete(f"{self.base_url}{endpoint}")
            if response.status_code == 204:
                return {"success": True}
            return self._handle_response(response)
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API server.")
            return {"error": True}
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")
            return {"error": True}


    def _handle_response(self, response) -> Dict:
        """Handle API response."""
        if response.status_code >= 400:
            try:
                error_detail = response.json()
                if isinstance(error_detail, dict) and "detail" in error_detail:
                    if isinstance(error_detail["detail"], list):
                        # FastAPI validation errors
                        errors = []
                        for error in error_detail["detail"]:
                            field = " -> ".join(error.get("loc", []))
                            msg = error.get("msg", "Unknown error")
                            errors.append(f"{field}: {msg}")
                        st.error(f"Validation Error: {'; '.join(errors)}")
                    else:
                        st.error(f"API Error: {error_detail['detail']}")
                else:
                    st.error(f"API Error: {error_detail}")
            except:
                st.error(f"API Error: {response.status_code} - {response.text}")
            return {"error": True, "status_code": response.status_code}

        try:
            return response.json()
        except:
            return {"success": True}


# Initialize API client
api = NugamotoAPI()


def main():
    st.set_page_config(
        page_title="Nugamoto Kitchen Management",
        page_icon="🍳",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS
    st.markdown("""
    <style>
    .stApp {
        background-color: #f0f2f6;
    }
    .main-header {
        background: linear-gradient(90deg, #ff6b6b 0%, #ffa500 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #ff6b6b;
    }
    .recipe-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🍳 Nugamoto Kitchen Management System</h1>
        <p>Your AI-Powered Recipe & Kitchen Companion</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/ff6b6b/ffffff?text=NUGAMOTO", use_column_width=True)
        st.markdown("---")

        page = st.selectbox(
            "🧭 Navigate to:",
            [
                "🏠 Dashboard",
                "👥 Users",
                "🏠 Kitchens",
                "🥘 Recipes",
                "📦 Inventory",
                "🛒 Shopping Lists",
                "🔧 Devices",
                "🍎 Food Items",
                "🤖 AI Recipe Generation",
                "⚙️ Settings"
            ]
        )

        st.markdown("---")
        st.markdown("**API Status**")

        # Check API health
        health_check = api.get("/")
        if not health_check.get("error"):
            st.success("✅ API Connected")
        else:
            st.error("❌ API Offline")

    # Route to different pages
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "👥 Users":
        show_users_page()
    elif page == "🏠 Kitchens":
        show_kitchens_page()
    elif page == "🥘 Recipes":
        show_recipes_page()
    elif page == "📦 Inventory":
        show_inventory_page()
    elif page == "🛒 Shopping Lists":
        show_shopping_page()
    elif page == "🔧 Devices":
        show_devices_page()
    elif page == "🍎 Food Items":
        show_food_items_page()
    elif page == "🤖 AI Recipe Generation":
        show_ai_recipe_page()
    elif page == "⚙️ Settings":
        show_settings_page()


def show_dashboard():
    """Show dashboard overview."""
    st.header("📊 Dashboard Overview")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    # Get summary statistics
    recipe_summary = api.get("/recipes/summary")
    if not recipe_summary.get("error"):
        with col1:
            st.metric(
                label="📚 Total Recipes",
                value=recipe_summary.get("total_recipes", 0),
                delta=None
            )

        with col2:
            st.metric(
                label="🤖 AI Generated",
                value=recipe_summary.get("ai_generated_recipes", 0),
                delta=None
            )

        with col3:
            avg_rating = recipe_summary.get("average_rating", 0)
            st.metric(
                label="⭐ Avg Rating",
                value=f"{avg_rating:.1f}",
                delta=None
            )

        with col4:
            st.metric(
                label="📝 Total Reviews",
                value=recipe_summary.get("total_reviews", 0),
                delta=None
            )

    st.markdown("---")

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Recipe Statistics")

        # Recipe difficulty distribution
        recipes = api.get("/recipes", params={"limit": 1000})
        if not recipes.get("error") and recipes:
            df = pd.DataFrame(recipes)
            if not df.empty:
                difficulty_counts = df['difficulty'].value_counts()

                fig = px.pie(
                    values=difficulty_counts.values,
                    names=difficulty_counts.index,
                    title="Recipe Difficulty Distribution",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏠 Kitchen Overview")

        # Kitchen stats
        kitchens = api.get("/kitchens")
        if not kitchens.get("error") and kitchens:
            kitchen_data = []
            for kitchen in kitchens[:5]:  # Show top 5 kitchens
                inventory = api.get(f"/inventory/{kitchen['id']}")
                item_count = len(inventory) if not inventory.get("error") else 0
                kitchen_data.append({
                    "Kitchen": kitchen["name"],
                    "Inventory Items": item_count,
                    "Users": len(kitchen.get("users", []))
                })

            if kitchen_data:
                df_kitchens = pd.DataFrame(kitchen_data)
                fig = px.bar(
                    df_kitchens,
                    x="Kitchen",
                    y="Inventory Items",
                    title="Inventory Items per Kitchen",
                    color="Inventory Items",
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(fig, use_container_width=True)

    # Recent recipes
    st.subheader("🆕 Recent Recipes")
    recent_recipes = api.get("/recipes", params={"limit": 5})
    if not recent_recipes.get("error") and recent_recipes:
        for recipe in recent_recipes:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                with col1:
                    st.write(f"**{recipe['title']}**")
                    st.caption(recipe.get('description', 'No description')[:100] + "...")

                with col2:
                    st.write(f"⏱️ {recipe.get('prep_time_minutes', 0)}min")

                with col3:
                    st.write(f"🔥 {recipe['difficulty']}")

                with col4:
                    if st.button("View", key=f"view_{recipe['id']}"):
                        st.session_state['selected_recipe_id'] = recipe['id']
                        st.rerun()

                st.markdown("---")


def show_recipes_page():
    """Show recipes management page."""
    st.header("🥘 Recipe Management")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 All Recipes", "➕ Create Recipe", "🔍 Recipe Details", "🍳 Cook Recipe"])

    with tab1:
        show_recipes_list()

    with tab2:
        show_create_recipe()

    with tab3:
        show_recipe_details()

    with tab4:
        show_cook_recipe_tab()


def show_recipes_list():
    """Show list of all recipes."""
    st.subheader("All Recipes")

    # Filters
    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            title_filter = st.text_input("Search by title")

        with col2:
            difficulty_filter = st.selectbox("Difficulty", ["All", "easy", "medium", "hard"])

        with col3:
            ai_generated_filter = st.selectbox("Type", ["All", "AI Generated", "User Created"])

        with col4:
            max_prep_time = st.number_input("Max prep time (min)", min_value=0, value=0)

    # Build query parameters
    params = {"limit": 50}
    if title_filter:
        params["title_contains"] = title_filter
    if difficulty_filter != "All":
        params["difficulty"] = difficulty_filter
    if ai_generated_filter == "AI Generated":
        params["is_ai_generated"] = True
    elif ai_generated_filter == "User Created":
        params["is_ai_generated"] = False
    if max_prep_time > 0:
        params["max_prep_time"] = max_prep_time

    # Get recipes
    recipes = api.get("/recipes", params=params)

    if not recipes.get("error") and recipes:
        st.write(f"Found {len(recipes)} recipes")

        # Display recipes in cards
        for i, recipe in enumerate(recipes):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])

                with col1:
                    st.markdown(f"### {recipe['title']}")
                    if recipe.get('description'):
                        st.caption(recipe['description'][:150] + "...")

                    # Tags
                    if recipe.get('tags'):
                        tags_str = " ".join([f"`{tag}`" for tag in recipe['tags'][:3]])
                        st.markdown(tags_str)

                with col2:
                    st.metric("⏱️ Prep", f"{recipe.get('prep_time_minutes', 0)}min")
                    st.metric("🔥 Cook", f"{recipe.get('cook_time_minutes', 0)}min")

                with col3:
                    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
                    st.metric("Difficulty", f"{difficulty_emoji.get(recipe['difficulty'], '⚪')} {recipe['difficulty']}")
                    st.metric("🍽️ Servings", recipe.get('servings', 'N/A'))

                with col4:
                    if st.button(f"👁️ View Details", key=f"view_detail_{recipe['id']}"):
                        st.session_state['selected_recipe_id'] = recipe['id']
                        st.rerun()

                    if st.button(f"🍳 Cook Now", key=f"cook_now_{recipe['id']}"):
                        st.session_state['cook_recipe_id'] = recipe['id']
                        st.rerun()

                st.markdown("---")
    else:
        st.info("No recipes found matching your criteria")


def show_create_recipe():
    """Show create recipe form."""
    st.subheader("Create New Recipe")

    with st.form("create_recipe_form", clear_on_submit=False):
        # Basic recipe info
        st.markdown("### 📝 Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            title = st.text_input("Recipe Title *", help="Enter a descriptive title for your recipe")
            description = st.text_area("Description", help="Brief description of the recipe")
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"])
            created_by_user_id = st.number_input("Created by User ID", min_value=1, value=1)

        with col2:
            prep_time = st.number_input("Prep Time (minutes)", min_value=1, value=15)
            cook_time = st.number_input("Cook Time (minutes)", min_value=1, value=30)
            servings = st.number_input("Servings", min_value=1, value=4)
            tags = st.text_input("Tags (comma separated)", placeholder="vegetarian, quick, healthy")

        st.markdown("---")

        # Ingredients section
        st.markdown("### 🥕 Ingredients")

        if 'ingredients' not in st.session_state:
            st.session_state.ingredients = [{"food_item_id": 1, "amount": 1.0, "unit": "g", "preparation": ""}]

        ingredients_container = st.container()

        with ingredients_container:
            for i, ingredient in enumerate(st.session_state.ingredients):
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 2, 1])

                with col1:
                    st.session_state.ingredients[i]["food_item_id"] = st.number_input(
                        f"Food Item ID",
                        min_value=1,
                        value=ingredient["food_item_id"],
                        key=f"food_{i}"
                    )

                with col2:
                    st.session_state.ingredients[i]["amount"] = st.number_input(
                        f"Amount",
                        min_value=0.1,
                        value=ingredient["amount"],
                        key=f"amount_{i}",
                        step=0.1
                    )

                with col3:
                    st.session_state.ingredients[i]["unit"] = st.text_input(
                        f"Unit",
                        value=ingredient["unit"],
                        key=f"unit_{i}"
                    )

                with col4:
                    st.session_state.ingredients[i]["preparation"] = st.text_input(
                        f"Preparation",
                        value=ingredient["preparation"],
                        key=f"prep_{i}",
                        placeholder="diced, chopped, etc."
                    )

                with col5:
                    if len(st.session_state.ingredients) > 1:
                        if st.button("❌", key=f"remove_ingredient_{i}"):
                            st.session_state.ingredients.pop(i)
                            st.rerun()

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.form_submit_button("➕ Add Ingredient"):
                st.session_state.ingredients.append({
                    "food_item_id": 1,
                    "amount": 1.0,
                    "unit": "g",
                    "preparation": ""
                })
                st.rerun()

        st.markdown("---")

        # Steps section
        st.markdown("### 👨‍🍳 Cooking Steps")

        if 'steps' not in st.session_state:
            st.session_state.steps = [{"step_number": 1, "instruction": ""}]

        steps_container = st.container()

        with steps_container:
            for i, step in enumerate(st.session_state.steps):
                col1, col2, col3 = st.columns([1, 4, 1])

                with col1:
                    st.session_state.steps[i]["step_number"] = st.number_input(
                        f"Step",
                        min_value=1,
                        value=step["step_number"],
                        key=f"step_num_{i}"
                    )

                with col2:
                    st.session_state.steps[i]["instruction"] = st.text_area(
                        f"Instruction {i + 1}",
                        value=step["instruction"],
                        key=f"instruction_{i}",
                        height=100
                    )

                with col3:
                    if len(st.session_state.steps) > 1:
                        if st.button("❌", key=f"remove_step_{i}"):
                            st.session_state.steps.pop(i)
                            st.rerun()

        if st.form_submit_button("➕ Add Step"):
            next_step = len(st.session_state.steps) + 1
            st.session_state.steps.append({
                "step_number": next_step,
                "instruction": ""
            })
            st.rerun()

        st.markdown("---")

        # Nutrition section (optional)
        st.markdown("### 🍎 Nutrition Information (Optional)")

        with st.expander("Add Nutrition Info"):
            col1, col2, col3 = st.columns(3)

            with col1:
                kcal = st.number_input("Calories (kcal)", min_value=0, value=0)
                protein_g = st.number_input("Protein (g)", min_value=0.0, value=0.0, step=0.1)
                carbs_g = st.number_input("Carbohydrates (g)", min_value=0.0, value=0.0, step=0.1)

            with col2:
                fat_g = st.number_input("Fat (g)", min_value=0.0, value=0.0, step=0.1)
                fiber_g = st.number_input("Fiber (g)", min_value=0.0, value=0.0, step=0.1)
                sugar_g = st.number_input("Sugar (g)", min_value=0.0, value=0.0, step=0.1)

            with col3:
                sodium_mg = st.number_input("Sodium (mg)", min_value=0.0, value=0.0, step=0.1)
                cholesterol_mg = st.number_input("Cholesterol (mg)", min_value=0.0, value=0.0, step=0.1)

        # Submit recipe
        st.markdown("---")
        submitted = st.form_submit_button("🍽️ Create Recipe", type="primary")

        if submitted:
            if title and st.session_state.ingredients and st.session_state.steps:
                # Validate ingredients
                valid_ingredients = []
                for ing in st.session_state.ingredients:
                    if ing["food_item_id"] > 0 and ing["amount"] > 0:
                        clean_ing = {
                            "food_item_id": ing["food_item_id"],
                            "amount": ing["amount"],
                            "unit": ing["unit"] if ing["unit"] else "piece"
                        }
                        if ing["preparation"]:
                            clean_ing["preparation"] = ing["preparation"]
                        valid_ingredients.append(clean_ing)

                # Validate steps
                valid_steps = []
                for step in st.session_state.steps:
                    if step["instruction"].strip():
                        valid_steps.append({
                            "step_number": step["step_number"],
                            "instruction": step["instruction"].strip()
                        })

                if not valid_ingredients:
                    st.error("❌ Please add at least one valid ingredient")
                    st.stop()

                if not valid_steps:
                    st.error("❌ Please add at least one cooking step")
                    st.stop()

                recipe_data = {
                    "title": title,
                    "description": description if description else None,
                    "difficulty": difficulty,
                    "prep_time_minutes": prep_time,
                    "cook_time_minutes": cook_time,
                    "servings": servings,
                    "tags": [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else [],
                    "created_by_user_id": created_by_user_id,
                    "ingredients": valid_ingredients,
                    "steps": valid_steps
                }

                # Add nutrition if provided
                if any([kcal, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg, cholesterol_mg]):
                    nutrition = {}
                    if kcal > 0:
                        nutrition["kcal"] = kcal
                    if protein_g > 0:
                        nutrition["protein_g"] = protein_g
                    if carbs_g > 0:
                        nutrition["carbs_g"] = carbs_g
                    if fat_g > 0:
                        nutrition["fat_g"] = fat_g
                    if fiber_g > 0:
                        nutrition["fiber_g"] = fiber_g
                    if sugar_g > 0:
                        nutrition["sugar_g"] = sugar_g
                    if sodium_mg > 0:
                        nutrition["sodium_mg"] = sodium_mg
                    if cholesterol_mg > 0:
                        nutrition["cholesterol_mg"] = cholesterol_mg

                    if nutrition:
                        recipe_data["nutrition"] = nutrition

                with st.spinner("Creating recipe..."):
                    result = api.post("/recipes", data=recipe_data)

                    if not result.get("error"):
                        st.success("✅ Recipe created successfully!")
                        st.balloons()

                        # Reset form
                        st.session_state.ingredients = [
                            {"food_item_id": 1, "amount": 1.0, "unit": "g", "preparation": ""}]
                        st.session_state.steps = [{"step_number": 1, "instruction": ""}]

                        # Show created recipe
                        st.info(
                            f"Created recipe: **{result.get('title', 'Unknown')}** (ID: {result.get('id', 'Unknown')})")
            else:
                st.error("❌ Please fill in all required fields: title, at least one ingredient, and at least one step")


def show_recipe_details():
    """Show detailed recipe view."""
    st.subheader("🔍 Recipe Details")

    recipe_id = st.session_state.get('selected_recipe_id', None)

    if not recipe_id:
        recipe_id = st.number_input("Enter Recipe ID", min_value=1, value=1)
        if st.button("Load Recipe"):
            st.session_state['selected_recipe_id'] = recipe_id
            st.rerun()

    if recipe_id:
        # Get recipe details
        recipe = api.get(f"/recipes/{recipe_id}/details")

        if not recipe.get("error"):
            # Header
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.title(recipe['title'])
                if recipe.get('description'):
                    st.write(recipe['description'])

                # Tags
                if recipe.get('tags'):
                    tags_html = " ".join([
                        f'<span style="background-color: #ff6b6b; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-right: 4px;">{tag}</span>'
                        for tag in recipe['tags']])
                    st.markdown(tags_html, unsafe_allow_html=True)

            with col2:
                st.metric("⏱️ Prep Time", f"{recipe.get('prep_time_minutes', 0)} min")
                st.metric("🔥 Cook Time", f"{recipe.get('cook_time_minutes', 0)} min")

            with col3:
                difficulty_colors = {"easy": "#4CAF50", "medium": "#FF9800", "hard": "#F44336"}
                difficulty_color = difficulty_colors.get(recipe['difficulty'], "#9E9E9E")
                st.markdown(
                    f'<div style="background-color: {difficulty_color}; color: white; padding: 8px; border-radius: 8px; text-align: center;"><strong>{recipe["difficulty"].upper()}</strong></div>',
                    unsafe_allow_html=True)
                st.metric("🍽️ Servings", recipe.get('servings', 'N/A'))

            st.markdown("---")

            # Two columns layout
            col1, col2 = st.columns([1, 1])

            with col1:
                # Ingredients
                st.subheader("🥕 Ingredients")

                if recipe.get('ingredients'):
                    for ingredient in recipe['ingredients']:
                        preparation = f" ({ingredient['preparation']})" if ingredient.get('preparation') else ""
                        st.write(
                            f"• **{ingredient['amount']} {ingredient['unit']}** - Food Item ID: {ingredient['food_item_id']}{preparation}")
                else:
                    st.info("No ingredients found")

                # Nutrition info
                if recipe.get('nutrition'):
                    st.subheader("🍎 Nutrition Information")
                    nutrition = recipe['nutrition']

                    col1_1, col1_2 = st.columns(2)

                    with col1_1:
                        if nutrition.get('kcal'):
                            st.metric("Calories", f"{nutrition['kcal']} kcal")
                        if nutrition.get('protein_g'):
                            st.metric("Protein", f"{nutrition['protein_g']}g")
                        if nutrition.get('carbs_g'):
                            st.metric("Carbs", f"{nutrition['carbs_g']}g")

                    with col1_2:
                        if nutrition.get('fat_g'):
                            st.metric("Fat", f"{nutrition['fat_g']}g")
                        if nutrition.get('fiber_g'):
                            st.metric("Fiber", f"{nutrition['fiber_g']}g")
                        if nutrition.get('sodium_mg'):
                            st.metric("Sodium", f"{nutrition['sodium_mg']}mg")

            with col2:
                # Cooking steps
                st.subheader("👨‍🍳 Cooking Instructions")

                if recipe.get('steps'):
                    for step in sorted(recipe['steps'], key=lambda x: x['step_number']):
                        st.markdown(f"""
                        <div style="background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #ff6b6b;">
                            <strong>Step {step['step_number']}</strong><br>
                            {step['instruction']}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No cooking steps found")

            st.markdown("---")

            # Action buttons
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("🍳 Cook This Recipe"):
                    st.session_state['cook_recipe_id'] = recipe['id']
                    st.rerun()

            with col2:
                if st.button("⭐ View Reviews"):
                    show_recipe_reviews(recipe['id'])

            with col3:
                if st.button("✏️ Edit Recipe"):
                    st.info("Edit functionality would go here")

            with col4:
                if st.button("🗑️ Delete Recipe"):
                    if st.button("Confirm Delete", type="primary"):
                        result = api.delete(f"/recipes/{recipe['id']}")
                        if not result.get("error"):
                            st.success("✅ Recipe deleted successfully!")
                            st.session_state.pop('selected_recipe_id', None)
                            st.rerun()

        else:
            st.error("❌ Recipe not found or error loading recipe details")


def show_cook_recipe_tab():
    """Show cook recipe interface."""
    st.subheader("🍳 Cook Recipe")

    cook_recipe_id = st.session_state.get('cook_recipe_id', None)

    if not cook_recipe_id:
        col1, col2 = st.columns(2)
        with col1:
            cook_recipe_id = st.number_input("Recipe ID to Cook", min_value=1, value=1)
        with col2:
            if st.button("Load Recipe for Cooking"):
                st.session_state['cook_recipe_id'] = cook_recipe_id
                st.rerun()

    if cook_recipe_id:
        # Get recipe details
        recipe = api.get(f"/recipes/{cook_recipe_id}")

        if not recipe.get("error"):
            st.success(f"Ready to cook: **{recipe['title']}**")

            # Get kitchens
            kitchens = api.get("/kitchens")

            if not kitchens.get("error") and kitchens:
                kitchen_options = {f"{kitchen['name']} (ID: {kitchen['id']})": kitchen['id'] for kitchen in kitchens}
                selected_kitchen = st.selectbox("Select Kitchen", list(kitchen_options.keys()))

                if selected_kitchen:
                    kitchen_id = kitchen_options[selected_kitchen]

                    # Show kitchen inventory
                    st.subheader("📦 Kitchen Inventory")
                    inventory = api.get(f"/inventory/{kitchen_id}")

                    if not inventory.get("error") and inventory:
                        inventory_df = pd.DataFrame(inventory)
                        if not inventory_df.empty:
                            st.dataframe(inventory_df[['food_item_id', 'quantity', 'unit', 'expiration_date']],
                                         use_container_width=True)

                    st.markdown("---")

                    # Cook button
                    col1, col2, col3 = st.columns([1, 1, 2])

                    with col2:
                        if st.button("🍳 Cook Recipe Now", type="primary", use_container_width=True):
                            with st.spinner("Cooking recipe..."):
                                result = api.post(f"/recipes/{cook_recipe_id}/cook", params={"kitchen_id": kitchen_id})

                                if not result.get("error"):
                                    st.success("✅ Recipe cooked successfully!")
                                    st.balloons()

                                    if result.get("updated_inventory_items"):
                                        st.info(f"Updated {len(result['updated_inventory_items'])} inventory items")

                                        # Show what was updated
                                        with st.expander("See inventory updates"):
                                            for item in result['updated_inventory_items']:
                                                st.write(
                                                    f"• Food Item {item['food_item_id']}: {item['old_quantity']} → {item['new_quantity']} {item['unit']}")

                                else:
                                    # Handle specific errors
                                    if result.get("status_code") == 422:
                                        st.error("❌ Insufficient ingredients!")
                                        if "insufficient_ingredients" in str(result):
                                            st.write("Missing ingredients:")
                                            # You could parse and show the missing ingredients here
            else:
                st.error("❌ No kitchens available or error loading kitchens")


def show_recipe_reviews(recipe_id: int):
    """Show reviews for a recipe."""
    st.subheader(f"⭐ Reviews for Recipe ID: {recipe_id}")

    # Get reviews
    reviews = api.get(f"/recipes/{recipe_id}/reviews")

    if not reviews.get("error") and reviews:
        # Rating summary
        rating_summary = api.get(f"/recipes/{recipe_id}/reviews/rating-summary")

        if not rating_summary.get("error"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Average Rating", f"{rating_summary.get('average_rating', 0):.1f}⭐")

            with col2:
                st.metric("Total Reviews", rating_summary.get('total_reviews', 0))

            with col3:
                st.metric("5-Star Reviews", rating_summary.get('rating_distribution', {}).get('5', 0))

        st.markdown("---")

        # Individual reviews
        for review in reviews:
            stars = "⭐" * review['rating']
            st.markdown(f"""
            <div style="background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                <strong>User {review['user_id']}</strong> - {stars} ({review['rating']}/5)<br>
                <em>{review.get('comment', 'No comment provided')}</em><br>
                <small>Reviewed on: {review.get('created_at', 'Unknown date')}</small>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.info("No reviews found for this recipe")


def show_kitchens_page():
    """Show kitchen management page."""
    st.header("🏠 Kitchen Management")

    tab1, tab2, tab3 = st.tabs(["📋 All Kitchens", "➕ Create Kitchen", "👥 Manage Users"])

    with tab1:
        show_kitchens_list()

    with tab2:
        show_create_kitchen()

    with tab3:
        show_kitchen_users()


def show_kitchens_list():
    """Show list of all kitchens."""
    st.subheader("All Kitchens")

    kitchens = api.get("/kitchens")

    if not kitchens.get("error") and kitchens:
        for kitchen in kitchens:
            with st.expander(f"🏠 {kitchen['name']}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Description:** {kitchen.get('description', 'No description')}")
                    st.write(f"**Created:** {kitchen.get('created_at', 'Unknown')}")

                with col2:
                    st.write(f"**Users:** {len(kitchen.get('users', []))}")

                    # Get inventory count
                    inventory = api.get(f"/inventory/{kitchen['id']}")
                    inventory_count = len(inventory) if not inventory.get("error") else 0
                    st.write(f"**Inventory Items:** {inventory_count}")

                with col3:
                    if st.button(f"📦 View Inventory", key=f"inventory_{kitchen['id']}"):
                        st.session_state['selected_kitchen_id'] = kitchen['id']
                        st.rerun()

                    if st.button(f"✏️ Edit", key=f"edit_kitchen_{kitchen['id']}"):
                        st.session_state['edit_kitchen_id'] = kitchen['id']
                        st.rerun()


def show_create_kitchen():
    """Show create kitchen form."""
    st.subheader("Create New Kitchen")

    with st.form("create_kitchen_form"):
        name = st.text_input("Kitchen Name *", placeholder="My Kitchen")
        description = st.text_area("Description", placeholder="Describe your kitchen...")

        submitted = st.form_submit_button("🏠 Create Kitchen")

        if submitted:
            if name:
                kitchen_data = {
                    "name": name,
                    "description": description if description else None
                }

                result = api.post("/kitchens", data=kitchen_data)

                if not result.get("error"):
                    st.success("✅ Kitchen created successfully!")
                    st.info(f"Created kitchen: **{result.get('name', 'Unknown')}** (ID: {result.get('id', 'Unknown')})")
            else:
                st.error("❌ Please enter a kitchen name")


def show_kitchen_users():
    """Show kitchen user management."""
    st.subheader("👥 Kitchen User Management")

    # Select kitchen
    kitchens = api.get("/kitchens")

    if not kitchens.get("error") and kitchens:
        kitchen_options = {f"{kitchen['name']} (ID: {kitchen['id']})": kitchen['id'] for kitchen in kitchens}
        selected_kitchen = st.selectbox("Select Kitchen", list(kitchen_options.keys()))

        if selected_kitchen:
            kitchen_id = kitchen_options[selected_kitchen]

            # Get kitchen details with users
            kitchen_details = api.get(f"/kitchens/{kitchen_id}")

            if not kitchen_details.get("error"):
                st.write(f"**Kitchen:** {kitchen_details['name']}")

                # Show current users
                if kitchen_details.get('users'):
                    st.subheader("Current Users")
                    users_df = pd.DataFrame(kitchen_details['users'])
                    st.dataframe(users_df[['id', 'username', 'email']], use_container_width=True)
                else:
                    st.info("No users in this kitchen")

                st.markdown("---")

                # Add user to kitchen
                st.subheader("Add User to Kitchen")

                col1, col2 = st.columns(2)

                with col1:
                    user_id_to_add = st.number_input("User ID to add", min_value=1, value=1)

                with col2:
                    if st.button("➕ Add User"):
                        result = api.post(f"/kitchens/{kitchen_id}/users/{user_id_to_add}")

                        if not result.get("error"):
                            st.success("✅ User added to kitchen!")
                            st.rerun()


def show_inventory_page():
    """Show inventory management."""
    st.header("📦 Inventory Management")

    tab1, tab2, tab3 = st.tabs(["📋 View Inventory", "➕ Add Item", "🔄 Update Item"])

    with tab1:
        show_inventory_list()

    with tab2:
        show_add_inventory_item()

    with tab3:
        show_update_inventory()


def show_inventory_list():
    """Show inventory for selected kitchen."""
    st.subheader("Kitchen Inventory")

    # Select kitchen
    kitchens = api.get("/kitchens")

    if not kitchens.get("error") and kitchens:
        kitchen_options = {f"{kitchen['name']} (ID: {kitchen['id']})": kitchen['id'] for kitchen in kitchens}
        selected_kitchen = st.selectbox("Select Kitchen", list(kitchen_options.keys()))

        if selected_kitchen:
            kitchen_id = kitchen_options[selected_kitchen]

            # Get inventory
            inventory = api.get(f"/inventory/{kitchen_id}")

            if not inventory.get("error") and inventory:
                # Convert to DataFrame for better display
                df_data = []
                for item in inventory:
                    df_data.append({
                        "Food Item ID": item['food_item_id'],
                        "Quantity": item['quantity'],
                        "Unit": item['unit'],
                        "Expiration": item.get('expiration_date', 'No expiration'),
                        "Location": item.get('storage_location', 'Not specified'),
                        "Added": item.get('created_at', 'Unknown')
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)

                # Expiration warnings
                today = datetime.now().date()
                expiring_soon = []

                for item in inventory:
                    if item.get('expiration_date'):
                        try:
                            exp_date = datetime.strptime(item['expiration_date'][:10], '%Y-%m-%d').date()
                            days_until_expiry = (exp_date - today).days

                            if days_until_expiry <= 3 and days_until_expiry >= 0:
                                expiring_soon.append({
                                    "food_item_id": item['food_item_id'],
                                    "days": days_until_expiry,
                                    "quantity": item['quantity'],
                                    "unit": item['unit']
                                })
                        except:
                            pass

                if expiring_soon:
                    st.warning("⚠️ Items expiring soon:")
                    for item in expiring_soon:
                        st.write(
                            f"• Food Item {item['food_item_id']}: {item['quantity']} {item['unit']} (expires in {item['days']} days)")

            else:
                st.info("No inventory items found for this kitchen")


def show_add_inventory_item():
    """Show add inventory item form."""
    st.subheader("Add Inventory Item")

    # Select kitchen
    kitchens = api.get("/kitchens")

    if not kitchens.get("error") and kitchens:
        kitchen_options = {f"{kitchen['name']} (ID: {kitchen['id']})": kitchen['id'] for kitchen in kitchens}
        selected_kitchen = st.selectbox("Select Kitchen", list(kitchen_options.keys()))

        if selected_kitchen:
            kitchen_id = kitchen_options[selected_kitchen]

            with st.form("add_inventory_item"):
                col1, col2 = st.columns(2)

                with col1:
                    food_item_id = st.number_input("Food Item ID", min_value=1, value=1)
                    quantity = st.number_input("Quantity", min_value=0.1, value=1.0, step=0.1)
                    unit = st.text_input("Unit", value="piece", placeholder="g, ml, piece, etc.")

                with col2:
                    expiration_date = st.date_input("Expiration Date (optional)", value=None)
                    storage_location = st.text_input("Storage Location (optional)", placeholder="Fridge, Pantry, etc.")

                submitted = st.form_submit_button("➕ Add to Inventory")

                if submitted:
                    inventory_data = {
                        "food_item_id": food_item_id,
                        "quantity": quantity,
                        "unit": unit
                    }

                    if expiration_date:
                        inventory_data["expiration_date"] = expiration_date.isoformat()

                    if storage_location:
                        inventory_data["storage_location"] = storage_location

                    result = api.post(f"/inventory/{kitchen_id}", data=inventory_data)

                    if not result.get("error"):
                        st.success("✅ Item added to inventory!")


def show_update_inventory():
    """Show update inventory interface."""
    st.subheader("Update Inventory Item")

    # Select kitchen
    kitchens = api.get("/kitchens")

    if not kitchens.get("error") and kitchens:
        kitchen_options = {f"{kitchen['name']} (ID: {kitchen['id']})": kitchen['id'] for kitchen in kitchens}
        selected_kitchen = st.selectbox("Select Kitchen", list(kitchen_options.keys()))

        if selected_kitchen:
            kitchen_id = kitchen_options[selected_kitchen]

            # Get current inventory
            inventory = api.get(f"/inventory/{kitchen_id}")

            if not inventory.get("error") and inventory:
                # Select item to update
                item_options = {}
                for item in inventory:
                    key = f"Food Item {item['food_item_id']} - {item['quantity']} {item['unit']}"
                    item_options[key] = item

                if item_options:
                    selected_item_key = st.selectbox("Select Item to Update", list(item_options.keys()))
                    selected_item = item_options[selected_item_key]

                    with st.form("update_inventory_item"):
                        col1, col2 = st.columns(2)

                        with col1:
                            new_quantity = st.number_input("New Quantity", min_value=0.1,
                                                           value=float(selected_item['quantity']), step=0.1)
                            new_unit = st.text_input("Unit", value=selected_item['unit'])

                        with col2:
                            current_exp = selected_item.get('expiration_date')
                            exp_value = None
                            if current_exp:
                                try:
                                    exp_value = datetime.strptime(current_exp[:10], '%Y-%m-%d').date()
                                except:
                                    pass

                            new_expiration = st.date_input("Expiration Date", value=exp_value)
                            new_location = st.text_input("Storage Location",
                                                         value=selected_item.get('storage_location', ''))

                        submitted = st.form_submit_button("🔄 Update Item")

                        if submitted:
                            update_data = {
                                "quantity": new_quantity,
                                "unit": new_unit
                            }

                            if new_expiration:
                                update_data["expiration_date"] = new_expiration.isoformat()

                            if new_location:
                                update_data["storage_location"] = new_location

                            result = api.patch(f"/inventory/{kitchen_id}/{selected_item['food_item_id']}",
                                               data=update_data)

                            if not result.get("error"):
                                st.success("✅ Inventory item updated!")
                                st.rerun()


def show_shopping_page():
    """Show shopping list management."""
    st.header("🛒 Shopping Lists")

    tab1, tab2, tab3 = st.tabs(["📋 View Lists", "➕ Create List", "✅ Manage Items"])

    with tab1:
        show_shopping_lists()

    with tab2:
        show_create_shopping_list()

    with tab3:
        show_manage_shopping_items()


def show_shopping_lists():
    """Show all shopping lists."""
    st.subheader("All Shopping Lists")

    shopping_lists = api.get("/shopping")

    if not shopping_lists.get("error") and shopping_lists:
        for shopping_list in shopping_lists:
            with st.expander(f"🛒 {shopping_list['name']} (Kitchen ID: {shopping_list['kitchen_id']})"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Description:** {shopping_list.get('description', 'No description')}")
                    st.write(f"**Created:** {shopping_list.get('created_at', 'Unknown')}")

                with col2:
                    # Get items count
                    items = api.get(f"/shopping/{shopping_list['id']}/items")
                    item_count = len(items) if not items.get("error") else 0
                    st.write(f"**Items:** {item_count}")

                with col3:
                    if st.button(f"👁️ View Items", key=f"view_shop_{shopping_list['id']}"):
                        st.session_state['selected_shopping_list_id'] = shopping_list['id']
                        st.rerun()

                # Show items if selected
                if st.session_state.get('selected_shopping_list_id') == shopping_list['id']:
                    show_shopping_list_items(shopping_list['id'])
    else:
        st.info("No shopping lists found")


def show_shopping_list_items(list_id: int):
    """Show items in a shopping list."""
    st.markdown("---")
    st.subheader(f"Items in Shopping List {list_id}")

    items = api.get(f"/shopping/{list_id}/items")

    if not items.get("error") and items:
        for item in items:
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                status_emoji = "✅" if item.get('is_purchased') else "⏳"
                st.write(f"{status_emoji} Food Item ID: {item['food_item_id']}")
                st.caption(f"Quantity: {item['quantity']} {item.get('unit', '')}")

            with col2:
                if item.get('notes'):
                    st.caption(f"Note: {item['notes']}")

            with col3:
                new_status = not item.get('is_purchased', False)
                action = "Mark Purchased" if not item.get('is_purchased') else "Mark Unpurchased"

                if st.button(action, key=f"toggle_{list_id}_{item['food_item_id']}"):
                    result = api.patch(f"/shopping/{list_id}/items/{item['food_item_id']}",
                                       data={"is_purchased": new_status})

                    if not result.get("error"):
                        st.rerun()
    else:
        st.info("No items in this shopping list")


def show_create_shopping_list():
    """Show create shopping list form."""
    st.subheader("Create Shopping List")

    # Get kitchens
    kitchens = api.get("/kitchens")

    if not kitchens.get("error") and kitchens:
        with st.form("create_shopping_list"):
            kitchen_options = {f"{kitchen['name']} (ID: {kitchen['id']})": kitchen['id'] for kitchen in kitchens}
            selected_kitchen = st.selectbox("Select Kitchen", list(kitchen_options.keys()))

            name = st.text_input("Shopping List Name *", placeholder="Weekly Groceries")
            description = st.text_area("Description", placeholder="Shopping list for this week...")

            submitted = st.form_submit_button("🛒 Create Shopping List")

            if submitted and name and selected_kitchen:
                kitchen_id = kitchen_options[selected_kitchen]

                list_data = {
                    "name": name,
                    "kitchen_id": kitchen_id,
                    "description": description if description else None
                }

                result = api.post("/shopping", data=list_data)

                if not result.get("error"):
                    st.success("✅ Shopping list created!")
                    st.info(f"Created: **{result.get('name', 'Unknown')}** (ID: {result.get('id', 'Unknown')})")


def show_manage_shopping_items():
    """Show shopping item management."""
    st.subheader("Manage Shopping Items")

    # Select shopping list
    shopping_lists = api.get("/shopping")

    if not shopping_lists.get("error") and shopping_lists:
        list_options = {f"{sl['name']} (ID: {sl['id']})": sl['id'] for sl in shopping_lists}
        selected_list = st.selectbox("Select Shopping List", list(list_options.keys()))

        if selected_list:
            list_id = list_options[selected_list]

            # Add new item
            st.subheader("Add Item")

            with st.form("add_shopping_item"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    food_item_id = st.number_input("Food Item ID", min_value=1, value=1)

                with col2:
                    quantity = st.number_input("Quantity", min_value=0.1, value=1.0, step=0.1)
                    unit = st.text_input("Unit", value="piece")

                with col3:
                    notes = st.text_area("Notes (optional)")

                if st.form_submit_button("➕ Add Item"):
                    item_data = {
                        "food_item_id": food_item_id,
                        "quantity": quantity,
                        "unit": unit
                    }

                    if notes:
                        item_data["notes"] = notes

                    result = api.post(f"/shopping/{list_id}/items", data=item_data)

                    if not result.get("error"):
                        st.success("✅ Item added to shopping list!")
                        st.rerun()


def show_food_items_page():
    """Show food items management."""
    st.header("🍎 Food Items")

    tab1, tab2, tab3 = st.tabs(["📋 All Food Items", "➕ Create Food Item", "🔍 Search Items"])

    with tab1:
        show_food_items_list()

    with tab2:
        show_create_food_item()

    with tab3:
        show_search_food_items()


def show_food_items_list():
    """Show list of all food items."""
    st.subheader("All Food Items")

    # Pagination controls
    col1, col2, col3 = st.columns(3)

    with col1:
        page_size = st.selectbox("Items per page", [20, 50, 100], index=1)

    with col2:
        page_number = st.number_input("Page", min_value=1, value=1)

    skip = (page_number - 1) * page_size

    # Get food items
    params = {"skip": skip, "limit": page_size}
    food_items = api.get("/food", params=params)

    if not food_items.get("error") and food_items:
        # Create a more readable display
        for item in food_items:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                with col1:
                    st.write(f"**{item['name']}** (ID: {item['id']})")
                    if item.get('description'):
                        st.caption(item['description'])

                with col2:
                    st.write(f"Category: {item.get('category', 'N/A')}")

                with col3:
                    st.write(f"Unit: {item.get('default_unit', 'N/A')}")

                with col4:
                    if st.button(f"📊 Details", key=f"food_detail_{item['id']}"):
                        show_food_item_details(item)

                st.markdown("---")

        # Navigation
        col1, col2, col3 = st.columns(3)
        with col1:
            if page_number > 1 and st.button("⬅️ Previous"):
                st.session_state['food_page'] = page_number - 1
                st.rerun()

        with col3:
            if len(food_items) == page_size and st.button("➡️ Next"):
                st.session_state['food_page'] = page_number + 1
                st.rerun()

    else:
        st.info("No food items found")


def show_food_item_details(item):
    """Show detailed food item information."""
    with st.expander(f"Details for {item['name']}", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**ID:** {item['id']}")
            st.write(f"**Name:** {item['name']}")
            st.write(f"**Category:** {item.get('category', 'N/A')}")
            st.write(f"**Default Unit:** {item.get('default_unit', 'N/A')}")

        with col2:
            st.write(f"**Description:** {item.get('description', 'N/A')}")
            st.write(f"**Created:** {item.get('created_at', 'Unknown')}")
            st.write(f"**Updated:** {item.get('updated_at', 'Unknown')}")


def show_create_food_item():
    """Show create food item form."""
    st.subheader("Create Food Item")

    with st.form("create_food_item"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Food Name *", placeholder="e.g., Tomato")
            category = st.text_input("Category", placeholder="e.g., Vegetables")
            default_unit = st.text_input("Default Unit", placeholder="e.g., piece, kg, ml")

        with col2:
            description = st.text_area("Description", placeholder="Brief description of the food item...")

        submitted = st.form_submit_button("🍎 Create Food Item")

        if submitted and name:
            food_data = {
                "name": name,
                "category": category if category else None,
                "default_unit": default_unit if default_unit else None,
                "description": description if description else None
            }

            result = api.post("/food", data=food_data)

            if not result.get("error"):
                st.success("✅ Food item created!")
                st.info(f"Created: **{result.get('name', 'Unknown')}** (ID: {result.get('id', 'Unknown')})")


def show_search_food_items():
    """Show food item search."""
    st.subheader("Search Food Items")

    col1, col2, col3 = st.columns(3)

    with col1:
        search_name = st.text_input("Search by name")

    with col2:
        search_category = st.text_input("Search by category")

    with col3:
        if st.button("🔍 Search"):
            params = {}
            if search_name:
                params["name_contains"] = search_name
            if search_category:
                params["category_contains"] = search_category

            results = api.get("/food", params=params)

            if not results.get("error") and results:
                st.write(f"Found {len(results)} items:")

                for item in results:
                    st.write(f"• **{item['name']}** (ID: {item['id']}) - {item.get('category', 'No category')}")
            else:
                st.info("No items found matching your search criteria")


def show_devices_page():
    """Show device/appliance management."""
    st.header("🔧 Kitchen Devices")

    tab1, tab2, tab3 = st.tabs(["📋 All Devices", "➕ Add Device", "🏠 By Kitchen"])

    with tab1:
        show_all_devices()

    with tab2:
        show_add_device()

    with tab3:
        show_devices_by_kitchen()


def show_all_devices():
    """Show all devices."""
    st.subheader("All Kitchen Devices")

    # Get device types first
    device_types = api.get("/devices/types")

    if not device_types.get("error") and device_types:
        st.write("**Available Device Types:**")
        for dtype in device_types:
            st.write(f"• {dtype['name']} - {dtype.get('description', 'No description')}")

    st.markdown("---")

    # Get all appliances
    appliances = api.get("/devices/appliances")

    if not appliances.get("error") and appliances:
        for appliance in appliances:
            with st.expander(f"🔧 {appliance['name']} (Kitchen: {appliance['kitchen_id']})"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Type:** {appliance.get('device_type_name', 'Unknown')}")
                    st.write(f"**Brand:** {appliance.get('brand', 'N/A')}")
                    st.write(f"**Model:** {appliance.get('model', 'N/A')}")

                with col2:
                    st.write(f"**Status:** {appliance.get('status', 'Unknown')}")
                    st.write(f"**Location:** {appliance.get('location', 'N/A')}")
                    st.write(f"**Added:** {appliance.get('created_at', 'Unknown')}")


def show_add_device():
    """Show add device form."""
    st.subheader("Add Kitchen Device")

    # Get kitchens and device types
    kitchens = api.get("/kitchens")
    device_types = api.get("/devices/types")

    if (not kitchens.get("error") and kitchens and
            not device_types.get("error") and device_types):

        with st.form("add_device"):
            col1, col2 = st.columns(2)

            with col1:
                kitchen_options = {f"{kitchen['name']} (ID: {kitchen['id']})": kitchen['id'] for kitchen in kitchens}
                selected_kitchen = st.selectbox("Select Kitchen", list(kitchen_options.keys()))

                device_type_options = {f"{dt['name']}": dt['id'] for dt in device_types}
                selected_device_type = st.selectbox("Device Type", list(device_type_options.keys()))

                name = st.text_input("Device Name *", placeholder="My Oven")
                brand = st.text_input("Brand", placeholder="Samsung")

            with col2:
                model = st.text_input("Model", placeholder="Model XYZ")
                location = st.text_input("Location in Kitchen", placeholder="Counter, Island, etc.")
                status = st.selectbox("Status", ["active", "inactive", "maintenance"])

            submitted = st.form_submit_button("🔧 Add Device")

            if submitted and name and selected_kitchen and selected_device_type:
                kitchen_id = kitchen_options[selected_kitchen]
                device_type_id = device_type_options[selected_device_type]

                device_data = {
                    "name": name,
                    "device_type_id": device_type_id,
                    "brand": brand if brand else None,
                    "model": model if model else None,
                    "location": location if location else None,
                    "status": status
                }

                result = api.post(f"/devices/appliances", params={"kitchen_id": kitchen_id}, data=device_data)

                if not result.get("error"):
                    st.success("✅ Device added successfully!")


def show_devices_by_kitchen():
    """Show devices grouped by kitchen."""
    st.subheader("Devices by Kitchen")

    kitchens = api.get("/kitchens")

    if not kitchens.get("error") and kitchens:
        for kitchen in kitchens:
            with st.expander(f"🏠 {kitchen['name']} Devices"):
                # Get appliances for this kitchen
                appliances = api.get(f"/devices/appliances/kitchen/{kitchen['id']}")

                if not appliances.get("error") and appliances:
                    for appliance in appliances:
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.write(f"**{appliance['name']}**")

                        with col2:
                            st.write(f"Type: {appliance.get('device_type_name', 'Unknown')}")

                        with col3:
                            st.write(f"Status: {appliance.get('status', 'Unknown')}")

                        with col4:
                            st.write(f"Location: {appliance.get('location', 'N/A')}")

                        st.markdown("---")
                else:
                    st.info("No devices found in this kitchen")


def show_users_page():
    """Show user management."""
    st.header("👥 User Management")

    tab1, tab2, tab3 = st.tabs(["📋 All Users", "➕ Create User", "👤 User Details"])

    with tab1:
        show_users_list()

    with tab2:
        show_create_user()

    with tab3:
        show_user_details()


def show_users_list():
    """Show list of all users."""
    st.subheader("All Users")

    users = api.get("/users")

    if not users.get("error") and users:
        # Create a table-like display
        for user in users:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

                with col1:
                    st.write(f"**{user['username']}** (ID: {user['id']})")
                    st.caption(user['email'])

                with col2:
                    st.write(f"Name: {user.get('first_name', '')} {user.get('last_name', '')}")
                    st.caption(f"Created: {user.get('created_at', 'Unknown')}")

                with col3:
                    st.write(f"Active: {'✅' if user.get('is_active') else '❌'}")

                with col4:
                    if st.button(f"👁️ Details", key=f"user_detail_{user['id']}"):
                        st.session_state['selected_user_id'] = user['id']
                        st.rerun()

                st.markdown("---")
    else:
        st.info("No users found")


def show_create_user():
    """Show create user form."""
    st.subheader("Create New User")

    with st.form("create_user"):
        col1, col2 = st.columns(2)

        with col1:
            username = st.text_input("Username *", placeholder="johndoe")
            email = st.text_input("Email *", placeholder="john@example.com")
            password = st.text_input("Password *", type="password")
            first_name = st.text_input("First Name", placeholder="John")

        with col2:
            last_name = st.text_input("Last Name", placeholder="Doe")
            phone = st.text_input("Phone", placeholder="+1234567890")
            date_of_birth = st.date_input("Date of Birth (optional)", value=None)
            is_active = st.checkbox("Active User", value=True)

        submitted = st.form_submit_button("👥 Create User")

        if submitted and username and email and password:
            user_data = {
                "username": username,
                "email": email,
                "password": password,
                "first_name": first_name if first_name else None,
                "last_name": last_name if last_name else None,
                "phone": phone if phone else None,
                "is_active": is_active
            }

            if date_of_birth:
                user_data["date_of_birth"] = date_of_birth.isoformat()

            result = api.post("/users", data=user_data)

            if not result.get("error"):
                st.success("✅ User created successfully!")
                st.info(f"Created user: **{result.get('username', 'Unknown')}** (ID: {result.get('id', 'Unknown')})")


def show_user_details():
    """Show detailed user information."""
    st.subheader("👤 User Details")

    user_id = st.session_state.get('selected_user_id', None)

    if not user_id:
        user_id = st.number_input("Enter User ID", min_value=1, value=1)
        if st.button("Load User"):
            st.session_state['selected_user_id'] = user_id
            st.rerun()

    if user_id:
        user = api.get(f"/users/{user_id}")

        if not user.get("error"):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader(f"{user['username']} (ID: {user['id']})")
                st.write(f"**Email:** {user['email']}")
                st.write(f"**Name:** {user.get('first_name', '')} {user.get('last_name', '')}")
                st.write(f"**Phone:** {user.get('phone', 'N/A')}")
                st.write(f"**Active:** {'✅ Yes' if user.get('is_active') else '❌ No'}")

            with col2:
                st.write(f"**Created:** {user.get('created_at', 'Unknown')}")
                st.write(f"**Updated:** {user.get('updated_at', 'Unknown')}")
                st.write(f"**Birth Date:** {user.get('date_of_birth', 'Not provided')}")

            # User's kitchens
            st.markdown("---")
            st.subheader("👥 Kitchens")

            # Get user's kitchens (you might need to implement this endpoint)
            kitchens = api.get("/kitchens")
            if not kitchens.get("error") and kitchens:
                user_kitchens = []
                for kitchen in kitchens:
                    for kitchen_user in kitchen.get('users', []):
                        if kitchen_user['id'] == user['id']:
                            user_kitchens.append(kitchen)
                            break

                if user_kitchens:
                    for kitchen in user_kitchens:
                        st.write(f"• **{kitchen['name']}** (ID: {kitchen['id']})")
                else:
                    st.info("User is not in any kitchens")

        else:
            st.error("❌ User not found or error loading user details")


def show_ai_recipe_page():
    """Show AI recipe generation page."""
    st.header("🤖 AI Recipe Generation")

    st.markdown("""
    Generate personalized recipes using AI based on your preferences, 
    available ingredients, and dietary requirements.
    """)

    tab1, tab2 = st.tabs(["🎯 Generate Recipe", "📊 AI Statistics"])

    with tab1:
        show_ai_recipe_generator()

    with tab2:
        show_ai_statistics()


def show_ai_recipe_generator():
    """Show AI recipe generation form."""
    st.subheader("Generate AI Recipe")

    # Get users and kitchens for selection
    users = api.get("/users")
    kitchens = api.get("/kitchens")

    if (not users.get("error") and users and
            not kitchens.get("error") and kitchens):

        with st.form("ai_recipe_generation"):
            # Basic info
            st.markdown("### 👤 Basic Information")
            col1, col2 = st.columns(2)

            with col1:
                user_options = {f"{user['username']} (ID: {user['id']})": user['id'] for user in users}
                selected_user = st.selectbox("Select User", list(user_options.keys()))

            with col2:
                kitchen_options = {f"{kitchen['name']} (ID: {kitchen['id']})": kitchen['id'] for kitchen in kitchens}
                selected_kitchen = st.selectbox("Select Kitchen", list(kitchen_options.keys()))

            st.markdown("---")

            # Recipe preferences
            st.markdown("### 🍽️ Recipe Preferences")
            col1, col2, col3 = st.columns(3)

            with col1:
                cuisine_type = st.text_input("Cuisine Type", placeholder="Italian, Asian, Mexican...")
                meal_type = st.selectbox("Meal Type", ["", "breakfast", "lunch", "dinner", "snack"])
                difficulty = st.selectbox("Difficulty", ["", "easy", "medium", "hard"])

            with col2:
                max_prep_time = st.number_input("Max Prep Time (minutes)", min_value=1, value=30)
                max_cook_time = st.number_input("Max Cook Time (minutes)", min_value=1, value=60)
                servings = st.number_input("Servings", min_value=1, value=4)

            with col3:
                prioritize_expiring = st.checkbox("Prioritize expiring ingredients", value=True)
                prefer_available = st.checkbox("Prefer available ingredients", value=True)

            st.markdown("---")

            # Dietary restrictions and preferences
            st.markdown("### 🥗 Dietary Restrictions")
            col1, col2 = st.columns(2)

            with col1:
                dietary_restrictions = st.multiselect(
                    "Dietary Restrictions",
                    ["vegetarian", "vegan", "gluten-free", "dairy-free", "nut-free", "low-carb", "keto", "paleo"]
                )

                exclude_ingredients = st.text_area(
                    "Ingredients to Exclude",
                    placeholder="mushrooms, olives, spicy foods..."
                )

            with col2:
                required_appliances = st.text_area(
                    "Required Appliances",
                    placeholder="oven, stovetop, blender..."
                )

                avoid_appliances = st.text_area(
                    "Avoid Appliances",
                    placeholder="microwave, deep fryer..."
                )

            st.markdown("---")

            # Special requests
            st.markdown("### 💭 Special Requests")
            special_requests = st.text_area(
                "Special Requests or Preferences",
                placeholder="Make it spicy, kid-friendly, quick and easy, comfort food...",
                height=100
            )

            # Generate button
            st.markdown("---")
            submitted = st.form_submit_button("🤖 Generate AI Recipe", type="primary")

            if submitted:
                if selected_user and selected_kitchen:
                    user_id = user_options[selected_user]
                    kitchen_id = kitchen_options[selected_kitchen]

                    # Build request data
                    request_data = {
                        "user_id": user_id,
                        "kitchen_id": kitchen_id,
                        "request": {
                            "prioritize_expiring": prioritize_expiring,
                            "prefer_available_ingredients": prefer_available,
                            "servings": servings,
                            "max_prep_time": max_prep_time,
                            "max_cook_time": max_cook_time
                        }
                    }

                    # Add optional fields
                    if cuisine_type:
                        request_data["request"]["cuisine_type"] = cuisine_type

                    if meal_type:
                        request_data["request"]["meal_type"] = meal_type

                    if difficulty:
                        request_data["request"]["difficulty_level"] = difficulty

                    if dietary_restrictions:
                        request_data["request"]["dietary_restrictions"] = dietary_restrictions

                    if exclude_ingredients:
                        request_data["request"]["exclude_ingredients"] = [
                            ing.strip() for ing in exclude_ingredients.split(",") if ing.strip()
                        ]

                    if required_appliances:
                        request_data["request"]["required_appliances"] = [
                            app.strip() for app in required_appliances.split(",") if app.strip()
                        ]

                    if avoid_appliances:
                        request_data["request"]["avoid_appliances"] = [
                            app.strip() for app in avoid_appliances.split(",") if app.strip()
                        ]

                    if special_requests:
                        request_data["request"]["special_requests"] = special_requests

                    # Make API call
                    with st.spinner("🤖 AI is generating your recipe... This may take a moment."):
                        result = api.post("/ai/generate-recipe", data=request_data)

                        if not result.get("error"):
                            st.success("✅ AI Recipe generated successfully!")
                            st.balloons()

                            # Display the generated recipe details
                            if result.get('recipe_id'):
                                st.info(f"🆕 New recipe created with ID: {result['recipe_id']}")

                                # Set the recipe ID to view details
                                st.session_state['selected_recipe_id'] = result['recipe_id']

                                if st.button("👁️ View Generated Recipe"):
                                    st.rerun()

                            # Display AI generation details
                            if result.get('ai_model_used'):
                                st.caption(f"Generated using: {result['ai_model_used']}")

                        else:
                            st.error("❌ Failed to generate AI recipe. Please try again.")


def show_ai_statistics():
    """Show AI generation statistics."""
    st.subheader("📊 AI Recipe Statistics")

    # Get AI-generated recipes
    ai_recipes = api.get("/recipes/ai-generated", params={"limit": 100})

    if not ai_recipes.get("error") and ai_recipes:
        st.metric("🤖 Total AI Recipes", len(ai_recipes))

        # Create statistics
        df = pd.DataFrame(ai_recipes)

        col1, col2 = st.columns(2)

        with col1:
            # Difficulty distribution
            if 'difficulty' in df.columns:
                difficulty_counts = df['difficulty'].value_counts()
                fig = px.pie(
                    values=difficulty_counts.values,
                    names=difficulty_counts.index,
                    title="AI Recipe Difficulty Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Servings distribution
            if 'servings' in df.columns:
                fig = px.histogram(
                    df,
                    x='servings',
                    title="AI Recipe Servings Distribution",
                    nbins=10
                )
                st.plotly_chart(fig, use_container_width=True)

        # Recent AI recipes
        st.subheader("🆕 Recent AI Recipes")
        recent_ai = ai_recipes[:5]

        for recipe in recent_ai:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"**{recipe['title']}**")
                    if recipe.get('description'):
                        st.caption(recipe['description'][:100] + "...")

                with col2:
                    st.write(f"⏱️ {recipe.get('prep_time_minutes', 0)}min")

                with col3:
                    st.write(f"🔥 {recipe['difficulty']}")

                st.markdown("---")

    else:
        st.info("No AI-generated recipes found")


def show_settings_page():
    """Show application settings."""
    st.header("⚙️ Settings")

    tab1, tab2, tab3 = st.tabs(["🔧 API Settings", "🎨 UI Settings", "ℹ️ About"])

    with tab1:
        show_api_settings()

    with tab2:
        show_ui_settings()

    with tab3:
        show_about()


def show_api_settings():
    """Show API configuration settings."""
    st.subheader("🔧 API Configuration")

    # Current API URL
    st.write(f"**Current API URL:** `{API_BASE_URL}`")

    # API Health Check
    health_check = api.get("/")
    if not health_check.get("error"):
        st.success("✅ API is responding")

        # Show API info if available
        if isinstance(health_check, dict):
            for key, value in health_check.items():
                st.write(f"**{key}:** {value}")
    else:
        st.error("❌ API is not responding")

    st.markdown("---")

    # Test API endpoints
    st.subheader("🧪 Test API Endpoints")

    test_endpoints = [
        ("/users", "Users"),
        ("/kitchens", "Kitchens"),
        ("/recipes", "Recipes"),
        ("/food", "Food Items")
    ]

    for endpoint, name in test_endpoints:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"**{name}:** `{endpoint}`")

        with col2:
            if st.button(f"Test", key=f"test_{endpoint}"):
                with st.spinner(f"Testing {endpoint}..."):
                    result = api.get(endpoint, params={"limit": 1})

                    if not result.get("error"):
                        st.success(f"✅ {name} OK")
                    else:
                        st.error(f"❌ {name} Failed")


def show_ui_settings():
    """Show UI customization settings."""
    st.subheader("🎨 UI Customization")

    # Theme settings
    st.write("**Theme Settings**")

    # These would be stored in session state or a config file
    theme = st.selectbox("Color Theme", ["Default", "Dark", "Light", "Custom"])

    if theme == "Custom":
        primary_color = st.color_picker("Primary Color", "#ff6b6b")
        secondary_color = st.color_picker("Secondary Color", "#ffa500")
        st.info("Custom theme settings would be applied here")

    # Layout settings
    st.markdown("---")
    st.write("**Layout Settings**")

    sidebar_state = st.selectbox("Default Sidebar State", ["Expanded", "Collapsed"])
    page_layout = st.selectbox("Page Layout", ["Wide", "Centered"])

    # Data display settings
    st.markdown("---")
    st.write("**Data Display Settings**")

    default_page_size = st.selectbox("Default Items Per Page", [10, 20, 50, 100])
    show_ids = st.checkbox("Show ID columns in tables", value=True)

    if st.button("💾 Save UI Settings"):
        st.success("✅ UI settings saved!")


def show_about():
    """Show application information."""
    st.subheader("ℹ️ About Nugamoto")

    st.markdown("""
    # 🍳 Nugamoto Kitchen Management System

    **Version:** 1.0.0  
    **Built with:** Streamlit + FastAPI  
    **Author:** AI Assistant  

    ## Features

    ✅ **Recipe Management** - Create, view, and organize recipes  
    ✅ **Kitchen Management** - Manage multiple kitchens and users  
    ✅ **Inventory Tracking** - Track ingredients and expiration dates  
    ✅ **Shopping Lists** - Create and manage shopping lists  
    ✅ **Device Management** - Track kitchen appliances  
    ✅ **AI Recipe Generation** - Generate recipes using AI  
    ✅ **Food Database** - Comprehensive food item database  

    ## API Endpoints

    This frontend connects to a FastAPI backend with the following main endpoints:

    - `/users` - User management
    - `/kitchens` - Kitchen management  
    - `/recipes` - Recipe operations
    - `/inventory` - Inventory management
    - `/shopping` - Shopping lists
    - `/food` - Food items database
    - `/devices` - Kitchen devices/appliances
    - `/ai` - AI recipe generation

    ## Support

    For support or feature requests, please contact the development team.
    """)

    # System information
    st.markdown("---")
    st.subheader("🔧 System Information")

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Streamlit Version:** {st.__version__}")
        st.write(f"**Python Version:** 3.x")
        st.write(f"**API Base URL:** {API_BASE_URL}")

    with col2:
        st.write(f"**Session State Keys:** {len(st.session_state)}")
        st.write(f"**Current Page:** {st.session_state.get('current_page', 'Dashboard')}")


if __name__ == "__main__":
    main()
