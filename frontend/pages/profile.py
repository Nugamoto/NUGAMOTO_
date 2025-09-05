"""User profile page for NUGAMOTO frontend."""

from __future__ import annotations

import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path
from frontend.utils.layout import render_sidebar

ensure_frontend_on_sys_path(__file__)


class ProfilePageController:
    def __init__(self) -> None:
        render_sidebar()


    @staticmethod
    def _ensure_user() -> dict | None:
        cu = st.session_state.get("current_user")
        if not isinstance(cu, dict):
            st.warning("Not signed in.")
            if st.button("Go to Login"):
                st.switch_page("pages/login.py")
            return None
        return cu


    def render(self) -> None:
        st.title("Profile")

        cu = self._ensure_user()
        if cu is None:
            return

        email = st.session_state.get("auth_email") or cu.get("email") or "unknown"
        user_id = cu.get("id", "unknown")
        is_admin = bool(st.session_state.get("is_admin", False))
        kitchen_name = st.session_state.get("selected_kitchen_name")
        kitchen_id = st.session_state.get("selected_kitchen_id")
        kitchen_role = st.session_state.get("selected_kitchen_role")

        st.subheader("Account")
        c1, c2, c3 = st.columns(3)
        c1.metric("User ID", user_id)
        c2.metric("Email", email)
        c3.metric("Role", "Admin" if is_admin else "User")

        st.subheader("Kitchen Context")
        if kitchen_id:
            k1, k2, k3 = st.columns(3)
            k1.metric("Kitchen", kitchen_name or "-")
            k2.metric("Kitchen ID", kitchen_id)
            k3.metric("Your Role", str(kitchen_role).title() if kitchen_role else "-")
        else:
            st.info("No kitchen selected.")

        st.subheader("Actions")
        a1, a2 = st.columns(2)
        if a1.button("Go to Dashboard"):
            st.switch_page("app.py")
        if a2.button("Logout"):
            st.session_state.auth_access_token = None
            st.session_state.auth_refresh_token = None
            st.session_state.auth_email = None
            st.session_state.is_admin = False
            st.session_state.current_user = None
            st.success("Signed out.")
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Profile - NUGAMOTO", page_icon="👤")
    ProfilePageController().render()


if __name__ == "__main__":
    main()
