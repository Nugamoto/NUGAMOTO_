"""Units Management Page for NUGAMOTO Admin."""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd
import streamlit as st

# Add frontend to path for runtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Direct imports for IDE resolution
try:
    from clients.units_client import UnitsClient
    from clients.base import APIException
except ImportError:
    # Fallback for different execution contexts
    from frontend.clients.units_client import UnitsClient
    from frontend.clients.base import APIException


class UnitsPageController:
    """Controller for Units management page."""


    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        """Initialize the Units page controller."""
        self.client = UnitsClient()
        # Tokens aus Session setzen (falls vorhanden)
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.client.set_tokens(access, refresh)
        self._initialize_session_state()

    @staticmethod
    def _initialize_session_state() -> None:
        """Initialize session state variables."""
        if "units_data" not in st.session_state:
            st.session_state.units_data = []
        if "show_create_form" not in st.session_state:
            st.session_state.show_create_form = False
        if "show_update_form" not in st.session_state:
            st.session_state.show_update_form = False
        if "selected_unit_for_update" not in st.session_state:
            st.session_state.selected_unit_for_update = None


    def load_units(self) -> list[dict[str, Any]]:
        """Load units from API with error handling."""
        try:
            units = self.client.list_units()
            st.session_state.units_data = units
            return units
        except APIException as e:
            st.error(f"Failed to load units: {e.message}")
            return []
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return []


    def create_unit(self, name: str, unit_type: str, to_base_factor: float) -> bool:
        """Create a new unit."""
        try:
            unit_data = {
                "name": name.lower().strip(),
                "type": unit_type,
                "to_base_factor": to_base_factor
            }

            created_unit = self.client.create_unit(unit_data)
            if created_unit:
                st.success(f"Unit '{name}' created successfully")
                st.session_state.show_create_form = False
                return True
            return False

        except APIException as e:
            st.error(f"Failed to create unit: {e.message}")
            return False
        except Exception as e:
            st.error(f"Validation error: {str(e)}")
            return False


    def update_unit(self, unit_id: int, name: str, unit_type: str, to_base_factor: float) -> bool:
        """Update an existing unit."""
        try:
            unit_data = {
                "name": name.lower().strip(),
                "type": unit_type,
                "to_base_factor": to_base_factor
            }

            updated_unit = self.client.update_unit(unit_id, unit_data)
            if updated_unit:
                st.success(f"Unit '{name}' updated successfully")
                st.session_state.show_update_form = False
                st.session_state.selected_unit_for_update = None
                return True
            return False

        except APIException as e:
            st.error(f"Failed to update unit: {e.message}")
            return False
        except Exception as e:
            st.error(f"Validation error: {str(e)}")
            return False


    def delete_unit(self, unit_id: int, unit_name: str) -> bool:
        """Delete a unit by ID."""
        try:
            self.client.delete_unit(unit_id)
            st.success(f"Unit '{unit_name}' deleted successfully")
            return True
        except APIException as e:
            st.error(f"Failed to delete unit: {e.message}")
            return False
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            return False


    def delete_multiple_units(self, unit_ids: list[int]) -> int:
        """Delete multiple units."""
        deleted_count = 0
        errors = []

        for unit_id in unit_ids:
            try:
                self.client.delete_unit(unit_id)
                deleted_count += 1
            except APIException as e:
                errors.append(f"Unit {unit_id}: {e.message}")

        if deleted_count > 0:
            st.success(f"Successfully deleted {deleted_count} units")

        if errors:
            st.error(f"Errors: {'; '.join(errors)}")

        return deleted_count


    def render_units_table(self, units: list[dict[str, Any]]) -> None:
        """Render the units data table with selection."""
        if not units:
            st.info("No units found. Create your first unit below.")
            return

        st.subheader(f"Units ({len(units)} total)")

        # Create DataFrame for better table handling
        df_data = []
        for unit in units:
            df_data.append({
                "ID": unit.get("id"),
                "Name": unit.get("name", "N/A"),
                "Type": unit.get("type", "N/A"),
                "Base Factor": unit.get("to_base_factor", 0),
                "Created": unit.get("created_at", "")[:10] if unit.get("created_at") else "N/A"
            })

        if df_data:
            df = pd.DataFrame(df_data)

            # Sort by ID as default
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
                selected_indices = event.selection.rows
                selected_units = [units[i] for i in selected_indices]

                st.write(f"**{len(selected_units)} unit(s) selected**")

                col1, col2, col3 = st.columns([1, 1, 3])

                with col1:
                    if st.button("🗑️ Delete Selected", type="secondary"):
                        selected_ids = [unit["id"] for unit in selected_units]
                        deleted = self.delete_multiple_units(selected_ids)
                        if deleted > 0:
                            st.rerun()

                with col2:
                    # Update button (only for single selection)
                    if len(selected_units) == 1:
                        if st.button("✏️ Edit Selected"):
                            st.session_state.selected_unit_for_update = selected_units[0]
                            st.session_state.show_update_form = True
                            st.rerun()
                    else:
                        st.button("✏️ Edit (Select 1)", disabled=True)


    def render_create_form(self) -> None:
        """Render the create unit form."""
        st.subheader("Create New Unit")

        with st.form("create_unit_form"):
            name = st.text_input("Unit Name", placeholder="e.g., kilogram")
            unit_type = st.selectbox(
                "Unit Type",
                options=["weight", "volume", "count", "measure", "package"]
            )
            to_base_factor = st.number_input(
                "Base Factor",
                min_value=0.0001,
                value=1.0,
                step=0.1
            )

            col_submit, col_cancel = st.columns([1, 1])

            with col_submit:
                submitted = st.form_submit_button("Create Unit", type="primary")

            with col_cancel:
                cancelled = st.form_submit_button("Cancel")

            if submitted and name and unit_type:
                success = self.create_unit(name, unit_type, to_base_factor)
                if success:
                    st.rerun()
            elif submitted:
                st.error("Please fill in all required fields.")

            if cancelled:
                st.session_state.show_create_form = False
                st.rerun()


    def render_update_form(self, unit: dict[str, Any]) -> None:
        """Render the update unit form."""
        st.subheader(f"Update Unit: {unit.get('name', 'Unknown')}")

        with st.form("update_unit_form"):
            name = st.text_input(
                "Unit Name",
                value=unit.get("name", ""),
                placeholder="e.g., kilogram"
            )
            unit_type = st.selectbox(
                "Unit Type",
                options=["weight", "volume", "count", "measure", "package"],
                index=["weight", "volume", "count", "measure", "package"].index(unit.get("type", "weight"))
            )
            to_base_factor = st.number_input(
                "Base Factor",
                min_value=0.0001,
                value=float(unit.get("to_base_factor", 1.0)),
                step=0.1
            )

            col_submit, col_cancel = st.columns([1, 1])

            with col_submit:
                submitted = st.form_submit_button("Update Unit", type="primary")

            with col_cancel:
                cancelled = st.form_submit_button("Cancel")

            if submitted and name and unit_type:
                success = self.update_unit(unit["id"], name, unit_type, to_base_factor)
                if success:
                    st.rerun()
            elif submitted:
                st.error("Please fill in all required fields.")

            if cancelled:
                st.session_state.show_update_form = False
                st.session_state.selected_unit_for_update = None
                st.rerun()


    def render_page(self) -> None:
        """Render the complete Units page."""
        st.title("Units Management")

        # Page controls
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("🔄 Refresh"):
                self.load_units()
                st.rerun()

        with col2:
            if st.button("➕ New Unit"):
                st.session_state.show_create_form = True
                st.rerun()

        st.divider()

        # Load and display units
        units = self.load_units()

        # Show create form if requested
        if st.session_state.show_create_form:
            self.render_create_form()
            st.divider()

        # Show update form if requested
        if st.session_state.show_update_form and st.session_state.selected_unit_for_update:
            self.render_update_form(st.session_state.selected_unit_for_update)
            st.divider()

        # Display units table
        self.render_units_table(units)


# Streamlit page entry point
controller = UnitsPageController()
controller.render_page()
