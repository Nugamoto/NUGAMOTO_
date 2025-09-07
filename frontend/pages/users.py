"""Users Management Page for NUGAMOTO (role-aware, PEP8 style)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path
from frontend.utils.layout import render_sidebar

ensure_frontend_on_sys_path(__file__)

from frontend.clients.base import APIException
from frontend.clients.users_client import UsersClient

class UsersController:
    """Encapsulates UI and API logic for the Users page with role-based actions."""

    def __init__(self) -> None:
        """Initialize the Users controller."""
        render_sidebar()
        self.users_client = UsersClient()

        # Attach tokens if available (routes are auth-protected)
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.users_client.set_tokens(access, refresh)

        # Role context for UI
        self.is_admin: bool = bool(getattr(st.session_state, "is_admin", False))
        cu = st.session_state.get("current_user") or {}
        self.current_user_id: int | None = int(cu.get("id")) if cu.get("id") is not None else None

        self._init_state()

    @staticmethod
    def _init_state() -> None:
        """Initialize default session-state values."""
        defaults: dict[str, Any] = {
            "users_rows": [],
            "show_add": False,
            "show_edit": False,
            "row_for_edit": None,
            "users_filter": "All",
        }
        for key, value in defaults.items():
            st.session_state.setdefault(key, value)


    # ---------------------------------------------------------------------
    # API interactions
    # ---------------------------------------------------------------------
    def _load_users(self) -> list[dict[str, Any]]:
        """Load users and cache them."""
        try:
            rows = self.users_client.list_users(limit=1000)
            st.session_state.users_rows = sorted(rows, key=lambda x: x["id"])
            return st.session_state.users_rows
        except APIException as exc:
            st.error(f"Failed to load users: {exc.message}")
            return []


    def _save_user(
            self,
            *,
            is_new: bool,
            payload: dict[str, Any],
            user_id: int | None = None,
    ) -> None:
        """Create or update a user via API."""
        try:
            if is_new:
                if not self.is_admin:
                    st.warning("Only admins can create users.")
                    return
                self.users_client.create_user(payload)
            else:
                # Allow admin to edit anyone; allow self to edit own account
                if not (self.is_admin or (self.current_user_id and self.current_user_id == user_id)):
                    st.warning("Only admins or the account owner can edit this user.")
                    return
                assert user_id is not None
                self.users_client.update_user(user_id, payload)

            st.success("User saved")
            st.session_state.show_add = False
            st.session_state.show_edit = False
            st.rerun()
        except APIException as exc:
            st.error(f"API error: {exc.message}")


    def _bulk_delete(self, user_ids: list[int]) -> None:
        """Delete multiple users (admin-only)."""
        if not self.is_admin:
            st.warning("Only admins can delete users from this view.")
            return

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


    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
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
        """Shorten long optional text for table display."""
        if not value:
            return "–"
        return value[:50] + "..." if len(value) > 50 else value

    @staticmethod
    def _format_diet_type(diet_type: str | None) -> str:
        """Normalize diet type for display."""
        if not diet_type:
            return "–"
        return diet_type.replace("-", " ").title()


    # ---------------------------------------------------------------------
    # Forms
    # ---------------------------------------------------------------------
    def _render_form(self, *, is_new: bool, defaults: dict[str, Any] | None = None) -> None:
        """Render add/edit form for a single user."""
        title = "Add User" if is_new else "Edit User"
        st.subheader(title)

        def _def(key: str) -> Any:
            return defaults.get(key) if defaults else None

        diet_type_options = [
            "",
            "omnivore",
            "vegetarian",
            "vegan",
            "pescetarian",
            "flexitarian",
            "carnivore",
        ]

        with st.form("user_form", clear_on_submit=is_new):
            # Basic
            st.subheader("Basic Information")
            email = st.text_input("Email *", value=_def("email") or "", disabled=not is_new)
            name = st.text_input("Name *", value=_def("name") or "")

            # Dietary
            st.subheader("Dietary Information")
            diet_type = st.selectbox(
                "Diet Type",
                diet_type_options,
                index=diet_type_options.index(_def("diet_type"))
                if _def("diet_type") in diet_type_options
                else 0,
                format_func=lambda x: "None" if x == "" else x.replace("-", " ").title(),
                help="Main dietary philosophy (e.g., vegetarian, vegan, omnivore)",
            )

            allergies = st.text_area(
                "Allergies & Restrictions",
                value=_def("allergies") or "",
                help="Medical dietary restrictions, allergies, intolerances, etc.",
                height=80,
            )

            preferences = st.text_area(
                "Food Preferences",
                value=_def("preferences") or "",
                help="Personal preferences (e.g., low-carb, organic only, spicy food).",
                height=80,
            )

            col_save, col_cancel = st.columns(2)
            can_save = bool(self.is_admin or (not is_new and self.current_user_id == _def("id")))
            save_clicked = col_save.form_submit_button(
                "Save",
                type="primary",
                disabled=not can_save and not is_new,
                help=None if can_save or is_new else "Only admins or the account owner can edit this user",
            )
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if save_clicked:
                if is_new and not self.is_admin:
                    st.warning("Only admins can create users.")
                    return

                if not email and is_new:
                    st.error("Email is required")
                    return
                if not name:
                    st.error("Name is required")
                    return

                payload: dict[str, Any] = {
                    "email": email if is_new else (_def("email") or ""),
                    "name": name,
                    "diet_type": diet_type if diet_type else None,
                    "allergies": allergies if allergies.strip() else None,
                    "preferences": preferences if preferences.strip() else None,
                }

                self._save_user(is_new=is_new, payload=payload, user_id=_def("id"))

            if cancel_clicked:
                st.session_state.show_add = False
                st.session_state.show_edit = False
                st.rerun()


    # ---------------------------------------------------------------------
    # Table rendering
    # ---------------------------------------------------------------------
    def render_table(self, rows: list[dict[str, Any]]) -> None:
        """Render users rows and handle selection actions."""
        if not rows:
            st.info("No users found.")
            return

        df = pd.DataFrame(
            {
                "ID": [r["id"] for r in rows],
                "Name": [r.get("name", "–") for r in rows],
                "Email": [r["email"] for r in rows],
                "Diet Type": [self._format_diet_type(r.get("diet_type")) for r in rows],
                "Allergies": [self._format_optional_field(r.get("allergies")) for r in rows],
                "Preferences": [self._format_optional_field(r.get("preferences")) for r in rows],
                "Created": [(r.get("created_at") or "")[:10] for r in rows],
                "Updated": [(r.get("updated_at") or "")[:10] for r in rows],
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

            col_del.button(
                "Delete Selected",
                type="secondary",
                disabled=not self.is_admin,
                help=None if self.is_admin else "Admin privileges required to delete users",
                on_click=lambda: self._bulk_delete([r["id"] for r in selected]),
            )

            if len(selected) == 1:
                selected_user_id = int(selected[0]["id"])
                can_edit = bool(self.is_admin or (self.current_user_id == selected_user_id))
                col_edit.button(
                    "Edit Selected",
                    disabled=not can_edit,
                    help=None if can_edit else "Only admins or the account owner can edit this user",
                    on_click=lambda: (
                        st.session_state.update(row_for_edit=selected[0], show_edit=True),
                        st.rerun(),
                    ),
                )
            else:
                col_edit.button("Edit (Select 1)", disabled=True)


    # ---------------------------------------------------------------------
    # Page composition
    # ---------------------------------------------------------------------
    def render(self) -> None:
        """Render action buttons, filters, forms, and table."""
        st.title("Users Management")

        col_ref, col_add, _ = st.columns([1, 1, 6])
        if col_ref.button("Refresh"):
            self._load_users()

        col_add.button(
            "Add User",
            disabled=not self.is_admin,
            help=None if self.is_admin else "Admin privileges required to add users",
            on_click=lambda: st.session_state.update(show_add=True),
        )

        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            selected_mode = st.selectbox(
                "Filter",
                (
                    "All",
                    "With Allergies",
                    "With Preferences",
                    "Omnivore",
                    "Vegetarian",
                    "Vegan",
                    "Pescetarian",
                    "Flexitarian",
                    "Carnivore",
                ),
                index=(
                    "All",
                    "With Allergies",
                    "With Preferences",
                    "Omnivore",
                    "Vegetarian",
                    "Vegan",
                    "Pescetarian",
                    "Flexitarian",
                    "Carnivore",
                ).index(st.session_state.users_filter),
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

        if st.session_state.show_add:
            self._render_form(is_new=True)

        if st.session_state.show_edit and st.session_state.row_for_edit:
            self._render_form(is_new=False, defaults=st.session_state.row_for_edit)

        all_rows = self._load_users()
        filtered_rows = self._apply_filter(all_rows)
        self.render_table(filtered_rows)


def main() -> None:
    """Streamlit page entry point."""
    st.set_page_config(page_title="Users - NUGAMOTO")
    UsersController().render()


if __name__ == "__main__":
    main()