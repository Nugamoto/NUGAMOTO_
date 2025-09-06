from __future__ import annotations

import streamlit as st

from frontend.utils.layout import render_sidebar
from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.clients.base import APIException
from frontend.clients.user_credentials_client import UserCredentialsClient


def _require_user_id() -> int | None:
    cu = st.session_state.get("current_user")
    if not isinstance(cu, dict) or cu.get("id") is None:
        st.switch_page("pages/login.py")
    return int(cu["id"])


def main() -> None:
    st.set_page_config(page_title="Edit Credentials - NUGAMOTO", page_icon="🔐")
    render_sidebar()

    user_id = _require_user_id()
    if not user_id:
        return

    client = UserCredentialsClient()
    access = st.session_state.get("auth_access_token")
    refresh = st.session_state.get("auth_refresh_token")
    if access:
        client.set_tokens(access, refresh)

    try:
        creds = client.get_user_credentials(user_id)
        mode = "edit"
    except APIException:
        creds = None
        mode = "create"


    def _def(key: str):
        return creds.get(key) if isinstance(creds, dict) else None


    with st.form("edit_credentials"):
        col_p, col_n = st.columns(2)
        with col_p:
            first_name = st.text_input("First Name", value=_def("first_name") or "")
        with col_n:
            last_name = st.text_input("Last Name", value=_def("last_name") or "")
        address = st.text_area("Address", value=_def("address") or "", height=80)
        col_city, col_zip, col_country = st.columns(3)
        with col_city:
            city = st.text_input("City", value=_def("city") or "")
        with col_zip:
            postal_code = st.text_input("Postal Code", value=_def("postal_code") or "")
        with col_country:
            country = st.text_input("Country", value=_def("country") or "")
        phone = st.text_input("Phone", value=_def("phone") or "")

        st.markdown("---")
        pw_col1, pw_col2 = st.columns(2)
        if mode == "create":
            password = pw_col1.text_input("Password", type="password")
            confirm_password = pw_col2.text_input("Confirm Password", type="password")
        else:
            new_password = pw_col1.text_input("New Password (optional)", type="password")
            confirm_new_password = pw_col2.text_input("Confirm New Password", type="password")

        col_s, col_c = st.columns(2)
        save = col_s.form_submit_button("Save", type="primary")
        cancel = col_c.form_submit_button("Cancel")

        if save:
            payload = {
                "first_name": first_name or None,
                "last_name": last_name or None,
                "address": address or None,
                "city": city or None,
                "postal_code": postal_code or None,
                "country": country or None,
                "phone": phone or None,
            }
            try:
                if mode == "create":
                    if not password:
                        st.error("Password required")
                        return
                    if password != confirm_password:
                        st.error("Passwords do not match")
                        return
                    payload["password_hash"] = password
                    client.create_user_credentials(user_id, payload)
                else:
                    if new_password or confirm_new_password:
                        if not new_password:
                            st.error("Please provide the new password")
                            return
                        if new_password != confirm_new_password:
                            st.error("New passwords do not match")
                            return
                        payload["password_hash"] = new_password
                    client.update_user_credentials(user_id, payload)
                st.success("Credentials saved")
                st.switch_page("pages/profile.py")
            except APIException as exc:
                st.error(f"Failed to save credentials: {exc.message}")

        if cancel:
            st.switch_page("pages/profile.py")


if __name__ == "__main__":
    main()
