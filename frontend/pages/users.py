"""
Users Management Page for NUGAMOTO Admin.

Features
--------
• View all users with complete backend data
• Add new users
• Edit existing users
• Bulk delete / single-row edit
• Filter bar: All · With Allergies · With Preferences · By Diet Type
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------ #
# Import path so IDE + runtime both resolve client modules           #
# ------------------------------------------------------------------ #
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from clients import (
        UsersClient,
        APIException,
    )
except ImportError:  # fallback for "python …"
    from frontend.clients import (
        UsersClient,
        APIException,
    )


class UsersController:
    """Encapsulates all UI and API logic for the users page."""


    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        self.users_client = UsersClient()
        # Tokens aus Session setzen (falls vorhanden)
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.users_client.set_tokens(access, refresh)
        self._init_state()


    @staticmethod
    def _init_state() -> None:
        defaults: dict[str, Any] = {
            "users_rows": [],
            "show_add": False,
            "show_edit": False,
            "row_for_edit": None,
            "users_filter": "All",
        }
        for key, val in defaults.items():
            st.session_state.setdefault(key, val)


    # ----------------------------- data loading ---------------------- #
    def _load_users(self) -> list[dict[str, Any]]:
        """Load users and cache them."""
        try:
            rows = self.users_client.list_users(limit=1000)
            st.session_state.users_rows = sorted(rows, key=lambda x: x["id"])
            return st.session_state.users_rows
        except APIException as exc:
            st.error(f"Failed to load users: {exc.message}")
            return []


    # ----------------------------- helpers --------------------------- #
    @staticmethod
    def _apply_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return rows filtered according to current selection."""
        mode = st.session_state.get("users_filter", "All")
        if mode == "With Allergies":
            return [r for r in rows if r.get("allergies")]
        if mode == "With Preferences":
            return [r for r in rows if r.get("preferences")]
        if mode == "Omnivore":
            return [r for r in rows if r.get("diet_type") == "omnivore"]
        if mode == "Vegetarian":
            return [r for r in rows if r.get("diet_type") == "vegetarian"]
        if mode == "Vegan":
            return [r for r in rows if r.get("diet_type") == "vegan"]
        if mode == "Pescetarian":
            return [r for r in rows if r.get("diet_type") == "pescetarian"]
        if mode == "Flexitarian":
            return [r for r in rows if r.get("diet_type") == "flexitarian"]
        if mode == "Carnivore":
            return [r for r in rows if r.get("diet_type") == "carnivore"]
        return rows


    @staticmethod
    def _format_optional_field(value: str | None) -> str:
        """Format optional fields for display."""
        if not value:
            return "–"
        # Truncate long text for table display
        return value[:50] + "..." if len(value) > 50 else value


    @staticmethod
    def _format_diet_type(diet_type: str | None) -> str:
        """Format diet type for display."""
        if not diet_type:
            return "–"
        return diet_type.replace("-", " ").title()


    # ------------------------- table rendering ----------------------- #
    def render_table(self, rows: list[dict[str, Any]]) -> None:
        """Render users rows and handle selection actions."""
        if not rows:
            st.info("No users found.")
            return

        # Build DataFrame with all available backend data
        df = pd.DataFrame(
            {
                "ID": [r["id"] for r in rows],
                "Name": [r.get("name", "–") for r in rows],
                "Email": [r["email"] for r in rows],
                "Diet Type": [self._format_diet_type(r.get("diet_type")) for r in rows],
                "Allergies": [self._format_optional_field(r.get("allergies")) for r in rows],
                "Preferences": [self._format_optional_field(r.get("preferences")) for r in rows],
                "Created": [r.get("created_at", "")[:10] if r.get("created_at") else "–" for r in rows],
                "Updated": [r.get("updated_at", "")[:10] if r.get("updated_at") else "–" for r in rows],
            }
        ).sort_values("ID")

        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun",
        )

        if event.selection.rows:
            selected = [rows[df.index[i]] for i in event.selection.rows]

            st.write(f"**{len(selected)} user(s) selected**")
            col_del, col_edit, _ = st.columns([1, 1, 6])

            if col_del.button("Delete Selected", type="secondary"):
                self._bulk_delete([r["id"] for r in selected])

            if len(selected) == 1:
                if col_edit.button("Edit Selected"):
                    st.session_state.row_for_edit = selected[0]
                    st.session_state.show_edit = True
                    st.rerun()


    # ----------------------------- CRUD helpers ---------------------- #
    def _bulk_delete(self, user_ids: list[int]) -> None:
        errors = 0
        for uid in user_ids:
            try:
                self.users_client.delete_user(uid)
            except APIException:
                errors += 1
        if errors:
            st.error(f"Failed to delete {errors} user(s)")
        else:
            st.success("User(s) deleted")
        st.rerun()


    def _save_user(
            self,
            *,
            is_new: bool,
            payload: dict[str, Any],
            user_id: int | None = None,
    ) -> None:
        try:
            if is_new:
                self.users_client.create_user(payload)
            else:
                assert user_id is not None
                self.users_client.update_user(user_id, payload)
            st.success("User saved")
            st.session_state.show_add = False
            st.session_state.show_edit = False
            st.rerun()
        except APIException as exc:
            st.error(f"API error: {exc.message}")


    # ------------------------- add / edit form ----------------------- #
    def _render_form(
            self,
            *,
            is_new: bool,
            defaults: dict[str, Any] | None = None,
    ) -> None:
        title = "Add User" if is_new else "Edit User"
        st.subheader(title)


        def _def(key: str) -> Any:
            return defaults.get(key) if defaults else None


        # Sinnvolle Diet Types - hauptsächlich Ernährungsphilosophien
        diet_type_options = [
            "",
            "omnivore",
            "vegetarian",
            "vegan",
            "pescetarian",
            "flexitarian",
            "carnivore"
        ]

        with st.form("user_form", clear_on_submit=is_new):
            # Basic Information
            st.subheader("Basic Information")

            email = st.text_input(
                "Email *",
                value=_def("email") or "",
                disabled=not is_new,  # Email usually shouldn't be changed
            )

            name = st.text_input(
                "Name *",
                value=_def("name") or "",
            )

            # Dietary Information
            st.subheader("Dietary Information")

            diet_type = st.selectbox(
                "Diet Type",
                diet_type_options,
                index=diet_type_options.index(_def("diet_type"))
                if _def("diet_type") in diet_type_options
                else 0,
                format_func=lambda x: "None" if x == "" else x.replace("-", " ").title(),
                help="Main dietary philosophy (e.g., vegetarian, vegan, omnivore)"
            )

            allergies = st.text_area(
                "Allergies & Restrictions",
                value=_def("allergies") or "",
                help="Food allergies, intolerances, and medical dietary restrictions (e.g., gluten-free, lactose intolerant, nut allergy)",
                height=80,
            )

            preferences = st.text_area(
                "Food Preferences",
                value=_def("preferences") or "",
                help="Personal food preferences, dislikes, and dietary choices (e.g., low-carb, organic only, spicy food)",
                height=80,
            )

            col_save, col_cancel = st.columns(2)
            if col_save.form_submit_button("Save", type="primary"):
                # Validation
                if not email:
                    st.error("Email is required")
                    return

                if not name:
                    st.error("Name is required")
                    return

                payload: dict[str, Any] = {
                    "email": email,
                    "name": name,
                    "diet_type": diet_type if diet_type else None,
                    "allergies": allergies if allergies.strip() else None,
                    "preferences": preferences if preferences.strip() else None,
                }

                self._save_user(
                    is_new=is_new,
                    payload=payload,
                    user_id=_def("id"),
                )

            if col_cancel.form_submit_button("Cancel"):
                st.session_state.show_add = False
                st.session_state.show_edit = False
                st.rerun()


    # ------------------------------ render --------------------------- #
    def render(self) -> None:
        """Main page renderer: action buttons above the filter and Apply/Clear filter
        buttons – aligned with the inventory-items page UX."""
        st.title("Users Management")

        # ----------------------------------------------------------------
        # Action buttons (Refresh / Add)    – first row
        # ----------------------------------------------------------------
        col_ref, col_add, _ = st.columns([1, 1, 6])
        if col_ref.button("Refresh"):
            self._load_users()
        if col_add.button("Add User"):
            st.session_state.show_add = True

        # ----------------------------------------------------------------
        # Filter selector with Apply / Clear buttons  – second row
        # ----------------------------------------------------------------
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])

        with col_f1:
            selected_mode = st.selectbox(
                "Filter",
                ("All", "With Allergies", "With Preferences", "Omnivore", "Vegetarian", "Vegan", "Pescetarian", "Flexitarian", "Carnivore"),
                index=("All", "With Allergies", "With Preferences", "Omnivore", "Vegetarian", "Vegan", "Pescetarian", "Flexitarian", "Carnivore").index(
                    st.session_state.users_filter
                ),
                key="users_filter_select",
            )

        with col_f2:
            if st.button("Apply Filter"):
                st.session_state.users_filter = selected_mode
                st.rerun()

        with col_f3:
            if st.button("Clear Filter"):
                st.session_state.users_filter = "All"
                st.rerun()

        st.divider()

        # ----------------------------------------------------------------
        # Forms (add / edit)
        # ----------------------------------------------------------------
        if st.session_state.show_add:
            self._render_form(is_new=True)

        if st.session_state.show_edit and st.session_state.row_for_edit:
            self._render_form(
                is_new=False,
                defaults=st.session_state.row_for_edit,
            )

        # ----------------------------------------------------------------
        # Data table
        # ----------------------------------------------------------------
        all_rows = self._load_users()
        filtered_rows = self._apply_filter(all_rows)
        self.render_table(filtered_rows)


# ----------------------------------------------------------------------
# Page entry point
# ----------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Users - NUGAMOTO")
    UsersController().render()


if __name__ == "__main__":
    main()