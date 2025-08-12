"""
User Credentials Management Page for NUGAMOTO Admin.

Features
--------
• View all user credentials with complete backend data
• Add credentials for users (only for users without credentials)
• Edit user credentials
• View detailed credential information
• Filters and client-side Advanced Search (name/city/country)
• Cached data loading with explicit refresh
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
        """Initialize default values in Streamlit session state."""
        defaults: dict[str, Any] = {
            "credentials_rows_all": [],
            "credentials_rows": [],
            "users_master": [],
            "show_add": False,
            "show_edit": False,
            "show_details": False,
            "show_search": False,
            "row_for_edit": None,
            "row_for_details": None,
            "credentials_filter": "All",
            "credentials_rows_loaded": False,
            "is_search_active": False,
            "cred_search_clear_requested": False,
        }
        for key, val in defaults.items():
            st.session_state.setdefault(key, val)


    # ----------------------------- data loading ---------------------- #
    def _load_master_data(self) -> None:
        """Load users into the session state."""
        try:
            st.session_state.users_master = self.users_client.list_users(limit=1000)
        except APIException as exc:
            st.error(f"Failed to load users: {exc.message}")


    def _load_credentials(self, *, force: bool = False) -> list[dict[str, Any]]:
        """Fetch credentials summaries unless cached or force=True.

        Keeps both the full dataset (credentials_rows_all) and the current
        view (credentials_rows). On reload, the view is reset to the full set.
        """
        try:
            if not force and st.session_state.credentials_rows_loaded:
                return st.session_state.credentials_rows

            rows = self.credentials_client.get_all_user_credentials_summary(limit=1000)
            rows = sorted(rows, key=lambda x: x["user_id"])

            st.session_state.credentials_rows_all = rows
            st.session_state.credentials_rows = rows.copy()

            st.session_state.credentials_rows_loaded = True
            st.session_state.is_search_active = False
            return st.session_state.credentials_rows
        except APIException as exc:
            st.error(f"Failed to load user credentials: {exc.message}")
            return []

    # ----------------------------- helpers --------------------------- #
    @staticmethod
    def _get_users_without_credentials() -> dict[str, int]:
        """Return users that do not yet have credentials.

        Always uses the full dataset (credentials_rows_all) so that search/filter
        in the current view does not affect availability calculations.
        """
        all_users = st.session_state.users_master
        full_creds = st.session_state.credentials_rows_all or st.session_state.credentials_rows
        users_with_creds = {row["user_id"] for row in full_creds}

        return {
            f'{user["name"]} ({user["email"]})': user["id"]
            for user in all_users
            if user["id"] not in users_with_creds
        }


    @staticmethod
    def _apply_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return rows filtered according to the current selection.

        Args:
            rows: Full list of credentials rows.

        Returns:
            Filtered list based on the active filter mode.
        """
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
        """Format optional text for table display.

        Args:
            value: Optional value.

        Returns:
            A string suitable for display (dash if missing).
        """
        return value if value else "–"

    @staticmethod
    def _get_user_email_by_id(user_id: int, users_list: list[dict[str, Any]]) -> str:
        """Resolve user email by ID from the master users list.

        Args:
            user_id: User identifier.
            users_list: Full list of users.

        Returns:
            Email address or a fallback label.
        """
        for user in users_list:
            if user["id"] == user_id:
                return user.get("email", f"user{user_id}@unknown")
        return f"user{user_id}@unknown"

    # ------------------------- table rendering ----------------------- #
    def render_table(self, rows: list[dict[str, Any]]) -> None:
        """Render credentials rows and handle selection actions.

        Args:
            rows: Rows to display (after filtering/search).
        """
        if not rows:
            st.info("No user credentials found.")
            return

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
        """Show all credential details in an expandable section.

        Args:
            credentials: Full credentials payload for a user.
        """
        with st.expander("📋 Complete User Credentials Details", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Identity")
                st.write(f"**User ID:** {credentials.get('user_id', 'N/A')}")
                st.write(
                    f"**Email:** {self._get_user_email_by_id(credentials.get('user_id', 0), st.session_state.users_master)}"
                )
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
                if credentials.get("full_address"):
                    st.write("**Full Address:**")
                    st.text(credentials["full_address"])

            st.subheader("System Information")
            col3, col4 = st.columns(2)
            with col3:
                st.write(f"**Created:** {credentials.get('created_at', 'N/A')}")
                st.write(f"**Updated:** {credentials.get('updated_at', 'N/A')}")
            with col4:
                st.write(f"**Password Hash:** {'***' if credentials.get('password_hash') else 'N/A'}")


    # ----------------------------- search form ----------------------- #
    def _render_search_form(self) -> None:
        """Render client-side Advanced Search (affects the view only)."""
        st.subheader("🔍 Advanced Search")

        # Clear request must be processed before creating widgets
        if st.session_state.get("cred_search_clear_requested"):
            for key in ("cred_search_name", "cred_search_city", "cred_search_country"):
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["cred_search_clear_requested"] = False

        with st.form("credentials_search_form"):
            col_left, col_right = st.columns(2)

            with col_left:
                name_q = st.text_input(
                    "Full Name contains",
                    value="",
                    key="cred_search_name",
                    placeholder="e.g. John",
                )
                city_q = st.text_input(
                    "City contains",
                    value="",
                    key="cred_search_city",
                    placeholder="e.g. Berlin",
                )

            with col_right:
                country_q = st.text_input(
                    "Country contains",
                    value="",
                    key="cred_search_country",
                    placeholder="e.g. Germany",
                )

            col_search, col_clear, col_cancel = st.columns(3)
            search_clicked = col_search.form_submit_button("🔍 Search", type="primary")
            clear_clicked = col_clear.form_submit_button("Clear")
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if search_clicked:
                # Always search against the full dataset (ground truth)
                base_rows = st.session_state.credentials_rows_all or self._load_credentials(force=True)

                def _contains(val: str | None, q: str) -> bool:
                    return bool(val) and q.lower() in val.lower()


                filtered = base_rows
                if name_q.strip():
                    filtered = [r for r in filtered if _contains(r.get("full_name"), name_q.strip())]
                if city_q.strip():
                    filtered = [r for r in filtered if _contains(r.get("city"), city_q.strip())]
                if country_q.strip():
                    filtered = [r for r in filtered if _contains(r.get("country"), country_q.strip())]

                st.session_state.credentials_rows = filtered
                st.session_state.credentials_rows_loaded = True
                st.session_state.is_search_active = True
                st.session_state.credentials_filter = "All"
                st.success(f"Found {len(filtered)} credential profile(s) matching criteria")
                st.rerun()

            if clear_clicked:
                st.session_state["cred_search_clear_requested"] = True
                st.session_state.is_search_active = False
                self._load_credentials(force=True)
                st.success("Search cleared")
                st.rerun()

            if cancel_clicked:
                st.session_state.show_search = False
                st.rerun()


    # ----------------------------- CRUD helpers ---------------------- #
    def _save_credentials(
            self,
            *,
            is_new: bool,
            user_id: int,
            payload: dict[str, Any],
    ) -> None:
        """Create or update a credentials record and handle UI state.

        Args:
            is_new: Create (True) or update (False).
            user_id: Target user ID.
            payload: Data to send to the API.
        """
        try:
            if is_new:
                self.credentials_client.create_user_credentials(user_id, payload)
            else:
                self.credentials_client.update_user_credentials(user_id, payload)
            st.success("User credentials saved")
            st.session_state.show_add = False
            st.session_state.show_edit = False
            # Reload to reflect changes
            self._load_credentials(force=True)
            st.rerun()
        except APIException as exc:
            st.error(f"API error: {exc.message}")


    # ------------------------- forms (add/edit) ---------------------- #
    def _render_credentials_form(
            self,
            *,
            is_new: bool,
            defaults: dict[str, Any] | None = None,
    ) -> None:
        """Render the Add/Edit Credentials form.

        Args:
            is_new: Whether form is for creation.
            defaults: Existing record (for edit).
        """
        st.subheader("Add User Credentials" if is_new else "Edit User Credentials")

        def _def(key: str) -> Any:
            return defaults.get(key) if defaults else None

        with st.form("credentials_form", clear_on_submit=is_new):
            # User selection only for new credentials
            if is_new:
                available_users = self._get_users_without_credentials()
                if not available_users:
                    st.warning("⚠️ All users already have credentials!")
                    st.info("Create new users first or edit existing credentials.")
                    close_clicked = st.form_submit_button("Close", type="secondary")
                    if close_clicked:
                        st.session_state.show_add = False
                        st.rerun()
                    return

                user_sel = st.selectbox(
                    "User *",
                    list(available_users.keys()),
                    help="Only users without existing credentials are shown",
                )
                selected_user_id = available_users[user_sel]
            else:
                user_email = self._get_user_email_by_id(_def("user_id"), st.session_state.users_master)
                st.text_input("User", value=f"User {_def('user_id')} ({user_email})", disabled=True)
                selected_user_id = _def("user_id")

            # Personal Information
            st.subheader("Personal Information")
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name", value=_def("first_name") or "")
            with col2:
                last_name = st.text_input("Last Name", value=_def("last_name") or "")

            # Address Information
            st.subheader("Address Information")
            address = st.text_area("Address", value=_def("address") or "", height=80)
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                city = st.text_input("City", value=_def("city") or "")
            with col_b:
                postal_code = st.text_input("Postal Code", value=_def("postal_code") or "")
            with col_c:
                country = st.text_input("Country", value=_def("country") or "")

            # Contact Information
            st.subheader("Contact Information")
            phone = st.text_input(
                "Phone",
                value=_def("phone") or "",
                help="Include country code (e.g., +1-555-0123)",
            )

            # Security (only for new credentials)
            if is_new:
                st.subheader("Security")
                password = st.text_input("Password *", type="password", help="This will be hashed before storage")
                confirm_password = st.text_input("Confirm Password *", type="password")

            # Submit buttons
            col_save, col_cancel = st.columns(2)
            save_clicked = col_save.form_submit_button("💾 Save", type="primary")
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if save_clicked:
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
                    payload["password_hash"] = f"hashed_{password}"

                self._save_credentials(
                    is_new=is_new,
                    user_id=selected_user_id,
                    payload=payload,
                )

            if cancel_clicked:
                st.session_state.show_add = False
                st.session_state.show_edit = False
                st.rerun()

    # ------------------------------ render --------------------------- #
    def render(self) -> None:
        """Main page renderer following the user_health pattern."""
        st.title("📇 User Credentials Management")

        # Load master users
        self._load_master_data()

        # Actions row
        col_ref, col_add, col_search, col_info = st.columns([1, 1, 1, 3])
        if col_ref.button("🔄 Refresh"):
            self._load_credentials(force=True)

        available_count = len(self._get_users_without_credentials())
        if col_add.button("➕ Add Credentials", disabled=available_count == 0):
            st.session_state.show_add = True

        if col_search.button("🔍 Advanced Search"):
            st.session_state.show_search = not st.session_state.show_search
            st.rerun()

        if available_count == 0:
            col_info.info("ℹ️ All users already have credentials")
        else:
            col_info.info(f"ℹ️ {available_count} users available for new credentials")

        # Filter row
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
                # Reset search and reload full dataset
                self._load_credentials(force=True)
                st.rerun()

        st.divider()

        # Advanced Search
        if st.session_state.show_search:
            self._render_search_form()
            st.divider()

        # Details view
        if st.session_state.show_details and st.session_state.row_for_details:
            self._show_detailed_view(st.session_state.row_for_details)
            st.divider()

        # Forms
        if st.session_state.show_add:
            self._render_credentials_form(is_new=True)

        if st.session_state.show_edit and st.session_state.row_for_edit:
            self._render_credentials_form(is_new=False, defaults=st.session_state.row_for_edit)

        # Data retrieval honoring cache/search state
        if not st.session_state.credentials_rows_loaded:
            all_rows = self._load_credentials()
        else:
            all_rows = st.session_state.credentials_rows

        filtered_rows = self._apply_filter(all_rows)
        self.render_table(filtered_rows)


# ----------------------------------------------------------------------
# Page entry point
# ----------------------------------------------------------------------
def main() -> None:
    """Streamlit app entry point for the credentials page."""
    st.set_page_config(page_title="User Credentials - NUGAMOTO", page_icon="📇")
    UserCredentialsController().render()


if __name__ == "__main__":
    main()