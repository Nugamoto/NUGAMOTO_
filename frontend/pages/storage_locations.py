"""Storage Locations Management Page for NUGAMOTO Admin."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from frontend.utils.layout import render_sidebar
from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.clients import StorageLocationsClient, APIException


class StorageLocationsController:
    """Controller for Storage Locations management page."""

    def __init__(self) -> None:
        render_sidebar()
        self.client = StorageLocationsClient()
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.client.set_tokens(access, refresh)
        self._initialize_session_state()

    @staticmethod
    def _initialize_session_state() -> None:
        if "storage_locations_data" not in st.session_state:
            st.session_state.storage_locations_data = []
        if "show_create_form" not in st.session_state:
            st.session_state.show_create_form = False
        if "show_update_form" not in st.session_state:
            st.session_state.show_update_form = False
        if "selected_location_for_update" not in st.session_state:
            st.session_state.selected_location_for_update = None

    def load_locations(self, kitchen_id: int) -> list[dict[str, Any]]:
        try:
            locations = self.client.list_storage_locations(kitchen_id=kitchen_id)
            st.session_state.storage_locations_data = sorted(locations, key=lambda x: x.get("id", 0))
            return st.session_state.storage_locations_data
        except APIException as e:
            if getattr(e, "status_code", None) == 403:
                st.warning(
                    "You don't have access to this kitchen's storage locations. "
                    "Open Kitchens to create your own kitchen or request access from an owner."
                )
                if st.button("Go to Kitchens", key="sl_go_kitchens"):
                    st.switch_page("pages/kitchens.py")
                return []
            st.error(f"Failed to load locations for Kitchen {kitchen_id}: {e.message}")
            return []

    def create_location(self, name: str, kitchen_id: int) -> bool:
        try:
            created = self.client.create_storage_location(name=name.strip(), kitchen_id=kitchen_id)
            if created:
                st.success(f"Location '{name}' created successfully.")
                st.session_state.show_create_form = False
                return True
            return False
        except APIException as e:
            st.error(f"Failed to create location: {e.message}")
            return False
        except Exception as e:
            st.error(f"A validation error occurred: {str(e)}")
            return False

    def update_location(self, location_id: int, name: str) -> bool:
        try:
            location_data = {"name": name.strip()}
            updated = self.client.update_storage_location(location_id, location_data)
            if updated:
                st.success(f"Location '{name}' updated successfully.")
                st.session_state.show_update_form = False
                st.session_state.selected_location_for_update = None
                return True
            return False
        except APIException as e:
            st.error(f"Failed to update location: {e.message}")
            return False
        except Exception as e:
            st.error(f"A validation error occurred: {str(e)}")
            return False

    def delete_locations(self, location_ids: list[int]) -> int:
        deleted_count = 0
        errors = []
        for location_id in location_ids:
            try:
                self.client.delete_storage_location(location_id)
                deleted_count += 1
            except APIException as e:
                errors.append(f"Location {location_id}: {e.message}")
        if deleted_count:
            st.success(f"Successfully deleted {deleted_count} location(s).")
        if errors:
            st.error(f"Errors: {'; '.join(errors)}")
        return deleted_count

    def render_locations_table(self, locations: list[dict[str, Any]]) -> None:
        if not locations:
            st.info("No storage locations found for this kitchen.")
            return

        st.subheader(f"Storage Locations ({len(locations)} total)")
        df_data = [
            {
                "ID": loc.get("id"),
                "Name": loc.get("name", "N/A"),
                "Created": loc.get("created_at", "")[:10],
                "Updated": loc.get("updated_at", "")[:10],
            }
            for loc in locations
        ]
        df = pd.DataFrame(df_data).sort_values("ID")
        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
        )
        if event.selection.rows:
            selected_indices = df.index[event.selection.rows].tolist()
            selected_locations = [locations[i] for i in selected_indices]

            st.write(f"**{len(selected_locations)} location(s) selected**")
            col1, col2, _ = st.columns([1, 1, 3])
            if col1.button("Delete Selected", type="secondary"):
                deleted = self.delete_locations([loc["id"] for loc in selected_locations])
                if deleted > 0:
                    st.rerun()
            if len(selected_locations) == 1:
                if col2.button("Edit Selected"):
                    st.session_state.selected_location_for_update = selected_locations[0]
                    st.session_state.show_update_form = True
                    st.rerun()
            else:
                col2.button("Edit (Select 1)", disabled=True)

    def render_create_form(self) -> None:
        with st.form("create_location_form"):
            st.subheader("Create New Storage Location")
            name = st.text_input("Location Name*", placeholder="e.g., Refrigerator")
            kitchen_id = int(st.session_state["selected_kitchen_id"])
            st.info(f"This location will be added to Kitchen ID: **{kitchen_id}**")

            c1, c2, _ = st.columns([1, 1, 4])
            if c1.form_submit_button("Create Location", type="primary"):
                if name:
                    if self.create_location(name, kitchen_id):
                        st.rerun()
                else:
                    st.error("Location name is required.")
            if c2.form_submit_button("Cancel"):
                st.session_state.show_create_form = False
                st.rerun()

    def render_update_form(self, location: dict[str, Any]) -> None:
        with st.form("update_location_form"):
            st.subheader(f"Update Location: {location.get('name', '')}")
            name = st.text_input("Location Name*", value=location.get("name", ""))
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.form_submit_button("Update Location", type="primary"):
                if name:
                    if self.update_location(location["id"], name):
                        st.rerun()
                else:
                    st.error("Location name is required.")
            if c2.form_submit_button("Cancel"):
                st.session_state.show_update_form = False
                st.session_state.selected_location_for_update = None
                st.rerun()

    def render(self) -> None:
        st.title("Storage Locations")

        if not st.session_state.get("selected_kitchen_id"):
            st.info("Please select a kitchen in the top bar to manage locations.")
            return

        kitchen_id = int(st.session_state["selected_kitchen_id"])
        st.divider()

        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("Refresh"):
            self.load_locations(kitchen_id)
        if c2.button("➕ New Location"):
            st.session_state.show_create_form = True
            st.session_state.show_update_form = False
            st.rerun()

        st.divider()

        locations = self.load_locations(kitchen_id)
        if st.session_state.show_create_form:
            self.render_create_form()
            st.divider()
        if st.session_state.show_update_form and st.session_state.selected_location_for_update:
            self.render_update_form(st.session_state.selected_location_for_update)
            st.divider()
        self.render_locations_table(locations)

def main() -> None:
    """Main function to run the page."""
    st.set_page_config(page_title="Storage Locations - NUGAMOTO")
    controller = StorageLocationsController()
    controller.render()


if __name__ == "__main__":
    main()
