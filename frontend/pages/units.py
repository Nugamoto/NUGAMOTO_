"""Units Management Page for NUGAMOTO (backend-enforced auth, PEP8 style)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path
from frontend.utils.layout import render_sidebar

ensure_frontend_on_sys_path(__file__)

from frontend.clients.base import APIException
from frontend.clients.units_client import UnitsClient


class UnitsPageController:
    """Controller for Units management page (let backend enforce auth)."""

    def __init__(self) -> None:
        """Initialize the Units page controller."""
        render_sidebar()
        self.client = UnitsClient()

        # Attach tokens if available (most routes are auth-protected)
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.client.set_tokens(access, refresh)

        self._init_state()

    @staticmethod
    def _init_state() -> None:
        """Initialize session-state variables used by this page."""
        st.session_state.setdefault("units_data", [])
        st.session_state.setdefault("show_create_form", False)
        st.session_state.setdefault("show_update_form", False)
        st.session_state.setdefault("selected_unit_for_update", None)

    # ---------------------------------------------------------------------
    # API interactions
    # ---------------------------------------------------------------------
    def load_units(self) -> list[dict[str, Any]]:
        """Load units from API with error handling."""
        try:
            units = self.client.list_units()
            st.session_state.units_data = units
            return units
        except APIException as exc:
            st.error(f"Failed to load units: {exc.message}")
            return []
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {str(exc)}")
            return []

    def create_unit(self, name: str, unit_type: str, to_base_factor: float) -> bool:
        """Create a new unit (backend enforces auth)."""
        try:
            payload = {
                "name": name.lower().strip(),
                "type": unit_type,
                "to_base_factor": to_base_factor,
            }
            created = self.client.create_unit(payload)
            if created:
                st.success(f"Unit '{name}' created successfully.")
                st.session_state.show_create_form = False
                return True
            return False
        except APIException as exc:
            if exc.status_code == 403:
                st.error("You are not allowed to create units (403).")
            else:
                st.error(f"Failed to create unit: {exc.message}")
            return False
        except Exception as exc:  # noqa: BLE001
            st.error(f"Validation error: {str(exc)}")
            return False

    def update_unit(
            self,
            unit_id: int,
            name: str,
            unit_type: str,
            to_base_factor: float,
    ) -> bool:
        """Update an existing unit (backend enforces auth)."""
        try:
            payload = {
                "name": name.lower().strip(),
                "type": unit_type,
                "to_base_factor": to_base_factor,
            }
            updated = self.client.update_unit(unit_id, payload)
            if updated:
                st.success(f"Unit '{name}' updated successfully.")
                st.session_state.show_update_form = False
                st.session_state.selected_unit_for_update = None
                return True
            return False
        except APIException as exc:
            if exc.status_code == 403:
                st.error("You are not allowed to update units (403).")
            else:
                st.error(f"Failed to update unit: {exc.message}")
            return False
        except Exception as exc:  # noqa: BLE001
            st.error(f"Validation error: {str(exc)}")
            return False

    def delete_unit(self, unit_id: int, unit_name: str) -> bool:
        """Delete a unit by ID (backend enforces auth)."""
        try:
            self.client.delete_unit(unit_id)
            st.success(f"Unit '{unit_name}' deleted successfully.")
            return True
        except APIException as exc:
            if exc.status_code == 403:
                st.error("You are not allowed to delete units (403).")
            else:
                st.error(f"Failed to delete unit: {exc.message}")
            return False
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {str(exc)}")
            return False

    def delete_multiple_units(self, unit_ids: list[int]) -> int:
        """Delete multiple units (backend enforces auth)."""
        deleted_count = 0
        errors: list[str] = []
        for uid in unit_ids:
            try:
                self.client.delete_unit(uid)
                deleted_count += 1
            except APIException as exc:
                msg = "not allowed (403)" if exc.status_code == 403 else exc.message
                errors.append(f"Unit {uid}: {msg}")

        if deleted_count > 0:
            st.success(f"Successfully deleted {deleted_count} unit(s).")
        if errors:
            st.error(f"Errors: {'; '.join(errors)}")
        return deleted_count

    # ---------------------------------------------------------------------
    # Rendering helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def _render_table(
            units: list[dict[str, Any]],
            on_delete: callable,
            on_edit: callable,
    ) -> None:
        """Render the units table with multi-selection and actions."""
        if not units:
            st.info("No units found. Create your first unit below.")
            return

        st.subheader(f"Units ({len(units)} total)")

        df = pd.DataFrame(
            [
                {
                    "ID": u.get("id"),
                    "Name": u.get("name") or "N/A",
                    "Type": u.get("type") or "N/A",
                    "Base Factor": u.get("to_base_factor", 0),
                    "Created": (u.get("created_at") or "")[:10],
                }
                for u in units
            ]
        ).sort_values("ID")

        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
        )

        if event.selection.rows:
            selected_units = [units[i] for i in event.selection.rows]
            st.write(f"**{len(selected_units)} unit(s) selected**")

            col_del, col_edit, _ = st.columns([1, 1, 3])

            col_del.button(
                "🗑️ Delete Selected",
                type="secondary",
                on_click=lambda: on_delete([u["id"] for u in selected_units]),
            )

            if len(selected_units) == 1:
                col_edit.button(
                    "✏️ Edit Selected",
                    on_click=lambda: on_edit(selected_units[0]),
                )
            else:
                col_edit.button("✏️ Edit (Select 1)", disabled=True)

    def render_create_form(self) -> None:
        """Render the create unit form."""
        st.subheader("Create New Unit")

        with st.form("create_unit_form"):
            name = st.text_input("Unit Name", placeholder="e.g., kilogram")
            unit_type = st.selectbox(
                "Unit Type", options=["weight", "volume", "count", "measure", "package"]
            )
            to_base_factor = st.number_input(
                "Base Factor", min_value=0.0001, value=1.0, step=0.1
            )

            col_submit, col_cancel = st.columns(2)
            submitted = col_submit.form_submit_button("Create Unit", type="primary")
            cancelled = col_cancel.form_submit_button("Cancel")

            if submitted and name and unit_type:
                if self.create_unit(name, unit_type, to_base_factor):
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
            name = st.text_input("Unit Name", value=unit.get("name", ""))
            type_options = ["weight", "volume", "count", "measure", "package"]
            current_type = unit.get("type", "weight")
            unit_type = st.selectbox(
                "Unit Type",
                options=type_options,
                index=type_options.index(current_type)
                if current_type in type_options
                else 0,
            )
            to_base_factor = st.number_input(
                "Base Factor",
                min_value=0.0001,
                value=float(unit.get("to_base_factor", 1.0)),
                step=0.1,
            )

            col_submit, col_cancel = st.columns(2)
            submitted = col_submit.form_submit_button("Update Unit", type="primary")
            cancelled = col_cancel.form_submit_button("Cancel")

            if submitted and name and unit_type:
                if self.update_unit(unit["id"], name, unit_type, to_base_factor):
                    st.rerun()
            elif submitted:
                st.error("Please fill in all required fields.")

            if cancelled:
                st.session_state.show_update_form = False
                st.session_state.selected_unit_for_update = None
                st.rerun()

    # ---------------------------------------------------------------------
    # Page composition
    # ---------------------------------------------------------------------
    def render(self) -> None:
        """Render the complete Units page."""
        st.title("Units Management")

        col_refresh, col_new = st.columns([1, 1])
        if col_refresh.button("🔄 Refresh"):
            self.load_units()
            st.rerun()

        if col_new.button("➕ New Unit"):
            st.session_state.show_create_form = True
            st.rerun()

        st.divider()

        units = self.load_units()

        if st.session_state.show_create_form:
            self.render_create_form()
            st.divider()

        if st.session_state.show_update_form and st.session_state.selected_unit_for_update:
            self.render_update_form(st.session_state.selected_unit_for_update)
            st.divider()

        def _on_delete_selected(ids: list[int]) -> None:
            deleted = self.delete_multiple_units(ids)
            if deleted > 0:
                st.rerun()

        def _on_edit_selected(unit_row: dict[str, Any]) -> None:
            st.session_state.selected_unit_for_update = unit_row
            st.session_state.show_update_form = True
            st.rerun()

        self._render_table(
            units=units,
            on_delete=_on_delete_selected,
            on_edit=_on_edit_selected,
        )


def main() -> None:
    """Streamlit page entry point."""
    st.set_page_config(page_title="Units - NUGAMOTO")
    UnitsPageController().render()


if __name__ == "__main__":
    main()