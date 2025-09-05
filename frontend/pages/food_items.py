"""Food Items Management Page for NUGAMOTO Admin."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.clients.food_items_client import FoodItemsClient
from frontend.clients.units_client import UnitsClient
from frontend.clients.base import APIException


class FoodItemsPageController:
    """Controller for Food Items management page."""


    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        """Initialize the Food Items page controller."""
        self.client = FoodItemsClient()
        self.units_client = UnitsClient()
        # Tokens aus Session setzen (falls vorhanden)
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.client.set_tokens(access, refresh)
            self.units_client.set_tokens(access, refresh)
        self._initialize_session_state()

    @staticmethod
    def _initialize_session_state() -> None:
        """Initialize session state variables."""
        if "food_items_data" not in st.session_state:
            st.session_state.food_items_data = []
        if "units_data" not in st.session_state:
            st.session_state.units_data = []
        if "show_create_form" not in st.session_state:
            st.session_state.show_create_form = False
        if "show_update_form" not in st.session_state:
            st.session_state.show_update_form = False
        if "selected_food_item_for_update" not in st.session_state:
            st.session_state.selected_food_item_for_update = None
        if "category_filter" not in st.session_state:
            st.session_state.category_filter = None


    def load_food_items(self, category: str | None = None) -> list[dict[str, Any]]:
        """Load food items from API with error handling."""
        try:
            food_items = self.client.list_food_items(category=category)
            # Sort by ID as default
            food_items_sorted = sorted(food_items, key=lambda x: x.get("id", 0))
            st.session_state.food_items_data = food_items_sorted
            return food_items_sorted
        except APIException as e:
            st.error(f"Failed to load food items: {e.message}")
            return []
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return []


    def load_units(self) -> list[dict[str, Any]]:
        """Load units for dropdown selection."""
        try:
            units = self.units_client.list_units()
            st.session_state.units_data = units
            return units
        except APIException as e:
            st.error(f"Failed to load units: {e.message}")
            return []
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return []


    def create_food_item(self, name: str, category: str, base_unit_id: int) -> bool:
        """Create a new food item."""
        try:
            food_item_data = {
                "name": name.strip(),
                "category": category.strip() if category else None,
                "base_unit_id": base_unit_id
            }

            created_food_item = self.client.create_food_item(food_item_data)
            if created_food_item:
                st.success(f"Food item '{name}' created successfully")
                st.session_state.show_create_form = False
                return True
            return False

        except APIException as e:
            st.error(f"Failed to create food item: {e.message}")
            return False
        except Exception as e:
            st.error(f"Validation error: {str(e)}")
            return False


    def update_food_item(self, food_item_id: int, name: str, category: str, base_unit_id: int) -> bool:
        """Update an existing food item."""
        try:
            food_item_data = {
                "name": name.strip(),
                "category": category.strip() if category else None,
                "base_unit_id": base_unit_id
            }

            updated_food_item = self.client.update_food_item(food_item_id, food_item_data)
            if updated_food_item:
                st.success(f"Food item '{name}' updated successfully")
                st.session_state.show_update_form = False
                st.session_state.selected_food_item_for_update = None
                return True
            return False

        except APIException as e:
            st.error(f"Failed to update food item: {e.message}")
            return False
        except Exception as e:
            st.error(f"Validation error: {str(e)}")
            return False


    def delete_food_item(self, food_item_id: int, food_item_name: str) -> bool:
        """Delete a food item by ID."""
        try:
            self.client.delete_food_item(food_item_id)
            st.success(f"Food item '{food_item_name}' deleted successfully")
            return True
        except APIException as e:
            st.error(f"Failed to delete food item: {e.message}")
            return False
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return False


    def delete_multiple_food_items(self, food_item_ids: list[int]) -> int:
        """Delete multiple food items."""
        deleted_count = 0
        errors = []

        for food_item_id in food_item_ids:
            try:
                self.client.delete_food_item(food_item_id)
                deleted_count += 1
            except APIException as e:
                errors.append(f"Food item {food_item_id}: {e.message}")

        if deleted_count > 0:
            st.success(f"Successfully deleted {deleted_count} food items")

        if errors:
            st.error(f"Errors: {'; '.join(errors)}")

        return deleted_count


    @staticmethod
    def get_available_categories(food_items: list[dict[str, Any]]) -> list[str]:
        """Extract unique categories from food items."""
        categories = set()
        for item in food_items:
            category = item.get("category")
            if category:
                categories.add(category)
        return sorted(list(categories))


    @staticmethod
    def get_unit_name_by_id(unit_id: int, units: list[dict[str, Any]]) -> str:
        """Get unit name by ID."""
        for unit in units:
            if unit.get("id") == unit_id:
                return unit.get("name", f"Unit {unit_id}")
        return f"Unit {unit_id}"


    def render_food_items_table(self, food_items: list[dict[str, Any]], units: list[dict[str, Any]]) -> None:
        """Render the food items data table with selection."""
        if not food_items:
            current_filter = st.session_state.get("category_filter")
            if current_filter:
                st.warning(f"No food items found in category '{current_filter}'. Try a different category.")
            else:
                st.info("No food items found. Create your first food item below.")
            return

        st.subheader(f"Food Items ({len(food_items)} total)")

        # Create DataFrame for better table handling
        df_data = []
        for item in food_items:
            base_unit_name = self.get_unit_name_by_id(item.get("base_unit_id", 0), units)
            df_data.append({
                "ID": item.get("id"),
                "Name": item.get("name", "N/A"),
                "Category": item.get("category", "N/A"),
                "Base Unit": base_unit_name,
                "Created": item.get("created_at", "")[:10] if item.get("created_at") else "N/A",
                "Updated": item.get("updated_at", "")[:10] if item.get("updated_at") else "N/A"
            })

        if df_data:
            df = pd.DataFrame(df_data)
            df = df.sort_values("ID")

            # Display table with multi-selection
            event = st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="multi-row"
            )

            # Actions for selected rows
            if event.selection.rows:
                # Use df.index to map correctly to original data
                selected_food_items = [food_items[df.index[i]] for i in event.selection.rows]

                st.write(f"**{len(selected_food_items)} food item(s) selected**")

                col1, col2, col3 = st.columns([1, 1, 3])

                with col1:
                    if st.button("Delete Selected", type="secondary"):
                        selected_ids = [item["id"] for item in selected_food_items]
                        deleted = self.delete_multiple_food_items(selected_ids)
                        if deleted > 0:
                            st.rerun()

                with col2:
                    if len(selected_food_items) == 1:
                        if st.button("Edit Selected"):
                            st.session_state.selected_food_item_for_update = selected_food_items[0]
                            st.session_state.show_update_form = True
                            st.rerun()
                    else:
                        st.button("Edit (Select 1)", disabled=True)


    def render_create_form(self, units: list[dict[str, Any]]) -> None:
        """Render the create food item form."""
        st.subheader("Create New Food Item")

        with st.form("create_food_item_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Food Item Name", placeholder="e.g., Tomato")
                category = st.text_input("Category", placeholder="e.g., Vegetable")

            with col2:
                # Unit selection dropdown
                unit_options = [(unit.get("id"), f"{unit.get('name', 'Unknown')} ({unit.get('type', 'N/A')})")
                                for unit in units]

                if unit_options:
                    selected_unit_index = st.selectbox(
                        "Base Unit",
                        range(len(unit_options)),
                        format_func=lambda x: unit_options[x][1],
                        help="Select the base unit for this food item"
                    )
                    base_unit_id = unit_options[selected_unit_index][0]
                else:
                    st.error("No units available. Please create units first.")
                    base_unit_id = None

            col_submit, col_cancel = st.columns([1, 1])

            with col_submit:
                submitted = st.form_submit_button("Create Food Item", type="primary")

            with col_cancel:
                cancelled = st.form_submit_button("Cancel")

            if submitted and name and base_unit_id:
                success = self.create_food_item(name, category, base_unit_id)
                if success:
                    st.rerun()
            elif submitted:
                st.error("Please fill in all required fields.")

            if cancelled:
                st.session_state.show_create_form = False
                st.rerun()


    def render_update_form(self, food_item: dict[str, Any], units: list[dict[str, Any]]) -> None:
        """Render the update food item form."""
        st.subheader(f"Update Food Item: {food_item.get('name', 'Unknown')}")

        with st.form("update_food_item_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input(
                    "Food Item Name",
                    value=food_item.get("name", ""),
                    placeholder="e.g., Tomato"
                )
                category = st.text_input(
                    "Category",
                    value=food_item.get("category", ""),
                    placeholder="e.g., Vegetable"
                )

            with col2:
                # Unit selection dropdown
                unit_options = [(unit.get("id"), f"{unit.get('name', 'Unknown')} ({unit.get('type', 'N/A')})")
                                for unit in units]

                if unit_options:
                    # Find current unit index
                    current_unit_id = food_item.get("base_unit_id")
                    current_index = 0
                    for i, (unit_id, _) in enumerate(unit_options):
                        if unit_id == current_unit_id:
                            current_index = i
                            break

                    selected_unit_index = st.selectbox(
                        "Base Unit",
                        range(len(unit_options)),
                        index=current_index,
                        format_func=lambda x: unit_options[x][1],
                        help="Select the base unit for this food item"
                    )
                    base_unit_id = unit_options[selected_unit_index][0]
                else:
                    st.error("No units available.")
                    base_unit_id = None

            col_submit, col_cancel = st.columns([1, 1])

            with col_submit:
                submitted = st.form_submit_button("Update Food Item", type="primary")

            with col_cancel:
                cancelled = st.form_submit_button("Cancel")

            if submitted and name and base_unit_id:
                success = self.update_food_item(food_item["id"], name, category, base_unit_id)
                if success:
                    st.rerun()
            elif submitted:
                st.error("Please fill in all required fields.")

            if cancelled:
                st.session_state.show_update_form = False
                st.session_state.selected_food_item_for_update = None
                st.rerun()


    def render_filters(self, all_food_items: list[dict[str, Any]]) -> None:
        """Render category filter controls."""
        categories = self.get_available_categories(all_food_items)

        if categories:
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                current_filter = st.session_state.get("category_filter")
                current_index = 0

                if current_filter in categories:
                    current_index = categories.index(current_filter) + 1

                selected_category = st.selectbox(
                    "Filter by Category",
                    options=["All Categories"] + categories,
                    index=current_index,
                    key="category_filter_select"
                )

            with col2:
                if st.button("Apply Filter"):
                    filter_value = None if selected_category == "All Categories" else selected_category
                    st.session_state.category_filter = filter_value
                    st.rerun()

            with col3:
                if st.button("Clear Filter"):
                    st.session_state.category_filter = None
                    st.rerun()


    def render_page(self) -> None:
        """Render the complete Food Items page."""
        st.title("Food Items Management")
        st.write("Manage food items and their base units for your kitchen inventory.")

        # Load units first
        units = self.load_units()

        # Page controls
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("Refresh"):
                current_filter = st.session_state.get("category_filter")
                self.load_food_items(current_filter)
                st.rerun()

        with col2:
            if st.button("New Food Item"):
                st.session_state.show_create_form = True
                st.rerun()

        st.divider()

        # Get current filter and load items
        current_filter = st.session_state.get("category_filter")
        food_items = self.load_food_items(current_filter)

        # Show filter status and controls
        if current_filter:
            st.info(f"Filtered by category: **{current_filter}**")

        # Render filter controls
        if not current_filter:
            self.render_filters(food_items)
        else:
            all_items = self.client.list_food_items()
            self.render_filters(all_items)

        st.divider()

        # Show create form if requested
        if st.session_state.show_create_form:
            self.render_create_form(units)
            st.divider()

        # Show update form if requested
        if st.session_state.show_update_form and st.session_state.selected_food_item_for_update:
            self.render_update_form(st.session_state.selected_food_item_for_update, units)
            st.divider()

        # Display food items table
        self.render_food_items_table(food_items, units)


# Streamlit page entry point
controller = FoodItemsPageController()
controller.render_page()
