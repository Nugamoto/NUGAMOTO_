"""
User Credentials Management Page for NUGAMOTO Admin.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from clients import (
        UserCredentialsClient,
        UsersClient,
        APIException,
    )
except ImportError:
    from frontend.clients import (
        UserCredentialsClient,
        UsersClient,
        APIException,
    )


class UserCredentialsController:
    """UI and API logic for the user credentials page."""

    def __init__(self) -> None:
        self.credentials_client = UserCredentialsClient()
        self.users_client = UsersClient()
        self._init_state()

    @staticmethod
    def _init_state() -> None:
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

    def _load_master_data(self) -> None:
        try:
            st.session_state.users_master = self.users_client.list_users(limit=1000)
        except APIException as exc:
            st.error(f"Failed to load users: {exc.message}")

    def _load_credentials(self, *, force: bool = False) -> list[dict[str, Any]]:
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

    @staticmethod
    def _get_users_without_credentials() -> dict[str, int]:
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
        return value if value else "–"

    @staticmethod
    def _get_user_email_by_id(user_id: int, users_list: list[dict[str, Any]]) -> str:
        for user in users_list:
            if user["id"] == user_id:
                return user.get("email", f"user{user_id}@unknown")
        return f"user{user_id}@unknown"

    def render_table(self, rows: list[dict[str, Any]]) -> None:
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

    def _show_detailed_view(self, credentials: dict[str, Any]) -> None:
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

    def _render_search_form(self) -> None:
        st.subheader("🔍 Advanced Search")

        if st.session_state.get("cred_search_clear_requested"):
            for key in ("cred_search_name", "cred_search_city", "cred_search_country"):
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["cred_search_clear_requested"] = False

        with st.form("credentials_search_form"):
            col_left, col_right = st.columns(2)

            with col_left:
                name_q = st.text_input("Full Name contains", value="", key="cred_search_name", placeholder="e.g. John")
                city_q = st.text_input("City contains", value="", key="cred_search_city", placeholder="e.g. Berlin")

            with col_right:
                country_q = st.text_input("Country contains", value="", key="cred_search_country",
                                          placeholder="e.g. Germany")

            col_search, col_clear, col_cancel = st.columns(3)
            search_clicked = col_search.form_submit_button("🔍 Search", type="primary")
            clear_clicked = col_clear.form_submit_button("Clear")
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if search_clicked:
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
            self._load_credentials(force=True)
            st.rerun()
        except APIException as exc:
            st.error(f"API error: {exc.message}")

    def _render_credentials_form(
            self,
            *,
            is_new: bool,
            defaults: dict[str, Any] | None = None,
    ) -> None:
        st.subheader("Add User Credentials" if is_new else "Edit User Credentials")

        def _def(key: str) -> Any:
            return defaults.get(key) if defaults else None

        with st.form("credentials_form", clear_on_submit=is_new):
            if is_new:
                available_users = self._get_users_without_credentials()
                if not available_users:
                    st.warning("All users already have credentials.")
                    st.form_submit_button("Close", disabled=True)
                    return

                user_sel = st.selectbox("User *", list(available_users.keys()))
                selected_user_id = available_users[user_sel]
            else:
                selected_user_id = _def("user_id")
                email = next((u.get("email", "") for u in st.session_state.users_master if u["id"] == selected_user_id),
                             "")
                st.text_input("User", value=f"User {selected_user_id} ({email})", disabled=True)

            st.subheader("Personal Information")
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name", value=_def("first_name") or "")
            with col2:
                last_name = st.text_input("Last Name", value=_def("last_name") or "")

            st.subheader("Address Information")
            address = st.text_area("Address", value=_def("address") or "", height=80)
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                city = st.text_input("City", value=_def("city") or "")
            with col_b:
                postal_code = st.text_input("Postal Code", value=_def("postal_code") or "")
            with col_c:
                country = st.text_input("Country", value=_def("country") or "")

            st.subheader("Contact Information")
            phone = st.text_input("Phone", value=_def("phone") or "", help="Include country code (e.g., +1-555-0123)")

            st.subheader("Security")
            if is_new:
                password = st.text_input("Password *", type="password", help="Will be hashed by the server")
                confirm_password = st.text_input("Confirm Password *", type="password")
            else:
                new_password = st.text_input("New Password (optional)", type="password")
                confirm_new_password = st.text_input("Confirm New Password", type="password")

            col_save, col_cancel = st.columns(2)
            save_clicked = col_save.form_submit_button("Save", type="primary")
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if save_clicked:
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
                    if not password:
                        st.error("Password is required")
                        return
                    if password != confirm_password:
                        st.error("Passwords don't match")
                        return
                    payload["password_hash"] = password  # plain; backend hashes
                else:
                    if new_password or confirm_new_password:
                        if not new_password:
                            st.error("Please provide the new password.")
                            return
                        if new_password != confirm_new_password:
                            st.error("New passwords do not match.")
                            return
                        payload["password_hash"] = new_password  # plain; backend hashes

                self._save_credentials(is_new=is_new, user_id=selected_user_id, payload=payload)

            if cancel_clicked:
                st.session_state.show_add = False
                st.session_state.show_edit = False
                st.rerun()

    def render(self) -> None:
        st.title("📇 User Credentials Management")
        self._load_master_data()

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
                self._load_credentials(force=True)
                st.rerun()

        st.divider()

        if st.session_state.show_search:
            self._render_search_form()
            st.divider()

        if st.session_state.show_details and st.session_state.row_for_details:
            self._show_detailed_view(st.session_state.row_for_details)
            st.divider()

        if st.session_state.show_add:
            self._render_credentials_form(is_new=True)

        if st.session_state.show_edit and st.session_state.row_for_edit:
            self._render_credentials_form(is_new=False, defaults=st.session_state.row_for_edit)

        if not st.session_state.credentials_rows_loaded:
            all_rows = self._load_credentials()
        else:
            all_rows = st.session_state.credentials_rows

        filtered_rows = self._apply_filter(all_rows)
        self.render_table(filtered_rows)


def main() -> None:
    st.set_page_config(page_title="User Credentials - NUGAMOTO", page_icon="📇")
    UserCredentialsController().render()


if __name__ == "__main__":
    main()