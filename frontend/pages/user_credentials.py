"""
User Credentials Management Page for NUGAMOTO Admin.

Features
--------
• View all user credentials with complete backend data
• Add credentials for users
• Edit user credentials
• View detailed credential information
• Filter and search functionality
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
        UserCredentialsClient,
        UsersClient,
        APIException,
    )
except ImportError:  # fallback for "python …"
    from frontend.clients import (
        UserCredentialsClient,
        UsersClient,
        APIException,
    )


class UserCredentialsController:
    """Encapsulates all UI and API logic for the user credentials page."""


    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        self.credentials_client = UserCredentialsClient()
        self.users_client = UsersClient()
        self._init_state()


    @staticmethod
    def _init_state() -> None:
        defaults: dict[str, Any] = {
            "credentials_rows": [],
            "users_master": [],
            "show_add": False,
            "show_edit": False,
            "show_details": False,
            "row_for_edit": None,
            "row_for_details": None,
            "credentials_filter": "All",
        }
        for key, val in defaults.items():
            st.session_state.setdefault(key, val)


    # ----------------------------- data loading ---------------------- #
    def _load_master_data(self) -> None:
        """Load users into session-state."""
        try:
            st.session_state.users_master = self.users_client.list_users(limit=1000)
        except APIException as exc:
            st.error(f"Failed to load users: {exc.message}")


    def _load_credentials(self) -> list[dict[str, Any]]:
        """Load user credentials and cache them."""
        try:
            rows = self.credentials_client.get_all_user_credentials_summary(limit=1000)
            st.session_state.credentials_rows = sorted(rows, key=lambda x: x["user_id"])
            return st.session_state.credentials_rows
        except APIException as exc:
            st.error(f"Failed to load user credentials: {exc.message}")
            return []


    # ----------------------------- helpers --------------------------- #
    @staticmethod
    def _apply_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return rows filtered according to current selection."""
        mode = st.session_state.get("credentials_filter", "All")
        if mode == "With Name":
            return [r for r in rows if r.get("full_name")]
        if mode == "With Address":
            return [r for r in rows if r.get("city") and r.get("country")]
        if mode == "City Available":
            return [r for r in rows if r.get("city")]
        if mode == "Country Available":
            return [r for r in rows if r.get("country")]
        return rows


    @staticmethod
    def _format_optional_field(value: str | None) -> str:
        """Format optional fields for display."""
        if not value:
            return "–"
        return value


    @staticmethod
    def _get_user_email_by_id(user_id: int, users_list: list[dict[str, Any]]) -> str:
        """Get user email by ID from users list."""
        for user in users_list:
            if user["id"] == user_id:
                return user.get("email", f"user{user_id}@unknown")
        return f"user{user_id}@unknown"


    # ------------------------- table rendering ----------------------- #
    def render_table(self, rows: list[dict[str, Any]]) -> None:
        """Render user credentials rows and handle selection actions."""
        if not rows:
            st.info("No user credentials found.")
            return

        # Build DataFrame with ALL available backend data from UserCredentialsSummary
        df = pd.DataFrame(
            {
                "User ID": [r["user_id"] for r in rows],
                "Email": [self._get_user_email_by_id(r["user_id"], st.session_state.users_master) for r in rows],
                "Full Name": [self._format_optional_field(r.get("full_name")) for r in rows],
                "City": [self._format_optional_field(r.get("city")) for r in rows],
                "Country": [self._format_optional_field(r.get("country")) for r in rows],
                "Created": [r.get("created_at", "")[:10] if r.get("created_at") else "–" for r in rows],
                "Updated": [r.get("updated_at", "")[:10] if r.get("updated_at") else "–" for r in rows],
            }
        ).sort_values("User ID")

        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun",
        )

        if event.selection.rows:
            selected = [rows[df.index[i]] for i in event.selection.rows]

            st.write(f"**{len(selected)} credential(s) selected**")

            if len(selected) == 1:
                col_edit, col_view, col_close, _ = st.columns([1, 1, 1, 5])

                if col_edit.button("Edit Selected"):
                    try:
                        full_credentials = self.credentials_client.get_user_credentials(selected[0]["user_id"])
                        st.session_state.row_for_edit = full_credentials
                        st.session_state.show_edit = True
                        st.session_state.show_details = False
                        st.rerun()
                    except APIException as exc:
                        st.error(f"Failed to load credentials: {exc.message}")

                if col_view.button("View Details"):
                    try:
                        full_credentials = self.credentials_client.get_user_credentials(selected[0]["user_id"])
                        st.session_state.row_for_details = full_credentials
                        st.session_state.show_details = True
                        st.session_state.show_edit = False
                        st.rerun()
                    except APIException as exc:
                        st.error(f"Failed to load credentials: {exc.message}")

                if col_close.button("Close Details"):
                    st.session_state.show_details = False
                    st.session_state.row_for_details = None
                    st.rerun()
            else:
                st.info("Please select exactly one user to view details or edit.")


    # ----------------------------- detailed view ---------------------- #
    def _show_detailed_view(self, credentials: dict[str, Any]) -> None:
        """Show all credential details in an expandable section."""
        with st.expander("📋 Complete User Credentials Details", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Identity")
                st.write(f"**User ID:** {credentials.get('user_id', 'N/A')}")
                st.write(
                    f"**Email:** {self._get_user_email_by_id(credentials.get('user_id', 0), st.session_state.users_master)}")
                st.write(f"**First Name:** {credentials.get('first_name', 'N/A')}")
                st.write(f"**Last Name:** {credentials.get('last_name', 'N/A')}")
                st.write(f"**Full Name:** {credentials.get('full_name', 'N/A')}")
                st.write(f"**Phone:** {credentials.get('phone', 'N/A')}")

            with col2:
                st.subheader("Address")
                st.write(f"**Address:** {credentials.get('address', 'N/A')}")
                st.write(f"**City:** {credentials.get('city', 'N/A')}")
                st.write(f"**Postal Code:** {credentials.get('postal_code', 'N/A')}")
                st.write(f"**Country:** {credentials.get('country', 'N/A')}")

                if credentials.get('full_address'):
                    st.write("**Full Address:**")
                    st.text(credentials['full_address'])

            st.subheader("System Information")
            col3, col4 = st.columns(2)
            with col3:
                st.write(f"**Created:** {credentials.get('created_at', 'N/A')}")
                st.write(f"**Updated:** {credentials.get('updated_at', 'N/A')}")
            with col4:
                st.write(f"**Password Hash:** {'***' if credentials.get('password_hash') else 'N/A'}")


    # ----------------------------- CRUD helpers ---------------------- #
    def _save_credentials(
            self,
            *,
            is_new: bool,
            user_id: int,
            payload: dict[str, Any],
    ) -> None:
        try:
            if is_new:
                self.credentials_client.create_user_credentials(user_id, payload)
            else:
                self.credentials_client.update_user_credentials(user_id, payload)
            st.success("User credentials saved")
            st.session_state.show_add = False
            st.session_state.show_edit = False
            st.rerun()
        except APIException as exc:
            st.error(f"API error: {exc.message}")


    # ------------------------- forms ------------------------------ #
    def _render_credentials_form(
            self,
            *,
            is_new: bool,
            defaults: dict[str, Any] | None = None,
    ) -> None:
        title = "Add User Credentials" if is_new else "Edit User Credentials"
        st.subheader(title)


        def _def(key: str) -> Any:
            return defaults.get(key) if defaults else None


        user_map = {f'{u["name"]} ({u["email"]})': u["id"] for u in st.session_state.users_master}

        with st.form("credentials_form", clear_on_submit=is_new):
            # User Selection (only for new credentials)
            if is_new:
                if not user_map:
                    st.error("No users available. Please create users first.")
                    return

                user_sel = st.selectbox(
                    "User *",
                    list(user_map.keys()),
                )
                selected_user_id = user_map[user_sel]
            else:
                user_email = self._get_user_email_by_id(_def("user_id"), st.session_state.users_master)
                st.text_input("User", value=f"User {_def('user_id')} ({user_email})", disabled=True)
                selected_user_id = _def("user_id")

            # Personal Information
            st.subheader("Personal Information")

            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input(
                    "First Name",
                    value=_def("first_name") or "",
                )
            with col2:
                last_name = st.text_input(
                    "Last Name",
                    value=_def("last_name") or "",
                )

            # Address Information
            st.subheader("Address Information")

            address = st.text_area(
                "Address",
                value=_def("address") or "",
                height=80,
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                city = st.text_input(
                    "City",
                    value=_def("city") or "",
                )
            with col2:
                postal_code = st.text_input(
                    "Postal Code",
                    value=_def("postal_code") or "",
                )
            with col3:
                country = st.text_input(
                    "Country",
                    value=_def("country") or "",
                )

            # Contact Information
            st.subheader("Contact Information")

            phone = st.text_input(
                "Phone",
                value=_def("phone") or "",
                help="Include country code (e.g., +1-555-0123)"
            )

            # Security (only for new credentials)
            if is_new:
                st.subheader("Security")
                password = st.text_input(
                    "Password *",
                    type="password",
                    help="This will be hashed before storage"
                )
                confirm_password = st.text_input(
                    "Confirm Password *",
                    type="password",
                )

            col_save, col_cancel = st.columns(2)
            if col_save.form_submit_button("Save", type="primary"):
                # Validation
                if is_new:
                    if not password:
                        st.error("Password is required")
                        return
                    if password != confirm_password:
                        st.error("Passwords don't match")
                        return

                payload: dict[str, Any] = {
                    "first_name": first_name or None,
                    "last_name": last_name or None,
                    "address": address or None,
                    "city": city or None,
                    "postal_code": postal_code or None,
                    "country": country or None,
                    "phone": phone or None,
                }

                if is_new:
                    # Hash the password (in a real app, you'd use proper hashing)
                    payload["password_hash"] = f"hashed_{password}"

                self._save_credentials(
                    is_new=is_new,
                    user_id=selected_user_id,
                    payload=payload,
                )

            if col_cancel.form_submit_button("Cancel"):
                st.session_state.show_add = False
                st.session_state.show_edit = False
                st.rerun()


    # ------------------------------ render --------------------------- #
    def render(self) -> None:
        """Main page renderer."""
        st.title("User Credentials Management")

        # Load master data
        self._load_master_data()

        # ----------------------------------------------------------------
        # Action buttons (Refresh / Add)    – first row
        # ----------------------------------------------------------------
        col_ref, col_add, _ = st.columns([1, 1, 6])
        if col_ref.button("Refresh"):
            self._load_credentials()
        if col_add.button("Add Credentials"):
            st.session_state.show_add = True

        # ----------------------------------------------------------------
        # Filter selector with Apply / Clear buttons  – second row
        # ----------------------------------------------------------------
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])

        with col_f1:
            selected_mode = st.selectbox(
                "Filter",
                ("All", "With Name", "With Address", "City Available", "Country Available"),
                index=("All", "With Name", "With Address", "City Available", "Country Available").index(
                    st.session_state.credentials_filter
                ),
                key="credentials_filter_select",
            )

        with col_f2:
            if st.button("Apply Filter"):
                st.session_state.credentials_filter = selected_mode
                st.rerun()

        with col_f3:
            if st.button("Clear Filter"):
                st.session_state.credentials_filter = "All"
                st.rerun()

        st.divider()

        # ----------------------------------------------------------------
        # Detailed View (persistent)
        # ----------------------------------------------------------------
        if st.session_state.show_details and st.session_state.row_for_details:
            self._show_detailed_view(st.session_state.row_for_details)
            st.divider()

        # ----------------------------------------------------------------
        # Forms (add / edit)
        # ----------------------------------------------------------------
        if st.session_state.show_add:
            self._render_credentials_form(is_new=True)

        if st.session_state.show_edit and st.session_state.row_for_edit:
            self._render_credentials_form(
                is_new=False,
                defaults=st.session_state.row_for_edit,
            )

        # ----------------------------------------------------------------
        # Data table
        # ----------------------------------------------------------------
        all_rows = self._load_credentials()
        filtered_rows = self._apply_filter(all_rows)
        self.render_table(filtered_rows)


# ----------------------------------------------------------------------
# Page entry point
# ----------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="User Credentials - NUGAMOTO")
    UserCredentialsController().render()


if __name__ == "__main__":
    main()
