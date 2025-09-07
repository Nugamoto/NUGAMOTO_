from __future__ import annotations

import streamlit as st

from frontend.utils.layout import render_sidebar
from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.clients.base import APIException
from frontend.clients.users_client import UsersClient


def _require_user_id() -> int | None:
    cu = st.session_state.get("current_user")
    if not isinstance(cu, dict) or cu.get("id") is None:
        st.switch_page("pages/login.py")
    return int(cu["id"])


def main() -> None:
    st.set_page_config(page_title="Edit Profile - NUGAMOTO", page_icon="✏️")
    render_sidebar()

    user_id = _require_user_id()
    if not user_id:
        return

    client = UsersClient()
    access = st.session_state.get("auth_access_token")
    refresh = st.session_state.get("auth_refresh_token")
    if access:
        client.set_tokens(access, refresh)

    try:
        user = client.get_user(user_id)
    except APIException:
        user = st.session_state.get("current_user") or {}

    diet_opts = ["", "omnivore", "vegetarian", "vegan", "pescetarian", "flexitarian", "carnivore"]
    with st.form("edit_user_profile"):
        diet_type = st.selectbox(
            "Diet Type",
            diet_opts,
            index=diet_opts.index(user.get("diet_type")) if user.get("diet_type") in diet_opts else 0,
        )
        allergies = st.text_area("Allergies", value=user.get("allergies") or "", height=80)
        preferences = st.text_area("Preferences", value=user.get("preferences") or "", height=80)

        col_s, col_c = st.columns(2)
        save = col_s.form_submit_button("Save", type="primary")
        cancel = col_c.form_submit_button("Cancel")

        if save:
            payload = {
                "diet_type": diet_type or None,
                "allergies": allergies.strip() or None,
                "preferences": preferences.strip() or None,
            }
            try:
                client.update_user(user_id, payload)
                st.success("Profile updated")
                st.switch_page("pages/profile.py")
            except APIException as exc:
                st.error(f"Failed to update profile: {exc.message}")

        if cancel:
            st.switch_page("pages/profile.py")


if __name__ == "__main__":
    main()
