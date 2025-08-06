"""
Inventory Management Page for NUGAMOTO Admin.

This page allows users to view, add, update, and delete items in the inventory
for a selected kitchen. It integrates data from food items, units, and storage
locations to provide a comprehensive management interface.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd
import streamlit as st

# Path setup for module resolution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Client and exception imports
try:
    from clients import (
        InventoryItemsClient,  # Updated name
        FoodItemsClient,
        StorageLocationsClient,
        APIException,
    )
except ImportError:
    from frontend.clients import (
        InventoryItemsClient,  # Updated name
        FoodItemsClient,
        StorageLocationsClient,
        APIException,
    )


class InventoryController:
    """Controller for the Inventory Management page."""


    def __init__(self) -> None:
        """Initialize the controller and its API clients."""
        self.inventory_client = InventoryItemsClient()  # Updated name
        self.food_items_client = FoodItemsClient()
        self.storage_locations_client = StorageLocationsClient()
        self._initialize_session_state()


    @staticmethod
    def _initialize_session_state() -> None:
        """Initialize all required session state variables for this page."""
        defaults = {
            "inventory_data": [],
            "food_items_master_list": [],
            "storage_locations_master_list": [],
            "selected_kitchen_id": 1,
            "show_add_form": False,
            "show_update_form": False,
            "selected_item_for_update": None,
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value


    def load_dependencies(self, kitchen_id: int) -> None:
        """Load all necessary data like food items and locations."""
        try:
            st.session_state.food_items_master_list = (
                self.food_items_client.list_food_items(limit=1000)
            )
            st.session_state.storage_locations_master_list = (
                self.storage_locations_client.list_storage_locations(kitchen_id)
            )
        except APIException as e:
            st.error(f"Failed to load dependencies: {e.message}")


    def load_inventory(self, kitchen_id: int) -> list[dict[str, Any]]:
        """Load inventory items for the selected kitchen."""
        try:
            inventory = self.inventory_client.list_inventory_items(kitchen_id)
            st.session_state.inventory_data = sorted(
                inventory, key=lambda x: x.get("id", 0)
            )
            return st.session_state.inventory_data
        except APIException as e:
            st.error(f"Failed to load inventory: {e.message}")
            return []

    @staticmethod
    def render_inventory_table(inventory: list[dict[str, Any]]) -> None:
        """Display the inventory data in a selectable table."""
        if not inventory:
            st.info("No inventory items found for this kitchen.")
            return

        st.subheader(f"Inventory Items ({len(inventory)} total)")
        df_data = [
            {
                "ID": item.get("id"),
                "Food Item": item.get("food_item", {}).get("name", "N/A"),
                "Location": item.get("storage_location", {}).get("name", "N/A"),
                "Quantity": f"{item.get('quantity', 0)} {item.get('food_item', {}).get('base_unit', {}).get('symbol', '')}",
                "Expires": item.get("expiration_date", "N/A"),
                "Updated": item.get("updated_at", "")[:10],
            }
            for item in inventory
        ]
        df = pd.DataFrame(df_data).sort_values("ID")
        st.dataframe(df, use_container_width=True, hide_index=True)

    @staticmethod
    def render_add_form() -> None:
        """Render the form to add a new inventory item."""
        st.subheader("Add New Inventory Item")
        # Placeholder for the actual form implementation
        st.info("Add/Update/Delete forms will be implemented in the next step.")


    def render(self) -> None:
        """Render the main page layout."""
        st.title("Inventory Management")

        kitchen_id = st.number_input(
            "Select Kitchen ID", min_value=1, step=1, key="selected_kitchen_id"
        )
        self.load_dependencies(kitchen_id)

        st.divider()
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("Refresh"):
            self.load_inventory(kitchen_id)
        if c2.button("➕ Add Item"):
            st.session_state.show_add_form = True

        st.divider()
        inventory = self.load_inventory(kitchen_id)
        if st.session_state.show_add_form:
            self.render_add_form()
            st.divider()
        self.render_inventory_table(inventory)


def main() -> None:
    """Run the Inventory page."""
    st.set_page_config(page_title="Inventory - NUGAMOTO")
    controller = InventoryController()
    controller.render()


if __name__ == "__main__":
    main()
