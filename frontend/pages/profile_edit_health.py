from __future__ import annotations

import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path
from frontend.utils.layout import render_sidebar

ensure_frontend_on_sys_path(__file__)

from frontend.clients.base import APIException
from frontend.clients.user_health_client import UserHealthClient


def _require_user_id() -> int | None:
    cu = st.session_state.get("current_user")
    if not isinstance(cu, dict) or cu.get("id") is None:
        st.switch_page("pages/login.py")
    return int(cu["id"])


def main() -> None:
    st.set_page_config(page_title="Edit Health - NUGAMOTO", page_icon="🏥")
    render_sidebar()

    user_id = _require_user_id()
    if not user_id:
        return

    client = UserHealthClient()
    access = st.session_state.get("auth_access_token")
    refresh = st.session_state.get("auth_refresh_token")
    if access:
        client.set_tokens(access, refresh)

    try:
        profile = client.get_user_health_profile(user_id)
        mode = "edit"
    except APIException:
        profile = None
        mode = "create"

    def _def(key: str):
        return profile.get(key) if isinstance(profile, dict) else None

    with st.form("edit_health"):
        col_a, col_b = st.columns(2)
        with col_a:
            age = st.number_input("Age", min_value=10, max_value=120, value=_def("age") or 25, step=1)
            gender_opts = ["", "male", "female", "other"]
            gender = st.selectbox(
                "Gender",
                gender_opts,
                index=gender_opts.index(_def("gender")) if _def("gender") in gender_opts else 0,
            )
        with col_b:
            height_cm = st.number_input("Height (cm)", min_value=50, max_value=300, value=_def("height_cm") or 170)
            weight_kg = st.number_input(
                "Weight (kg)",
                min_value=20.0,
                max_value=500.0,
                value=_def("weight_kg") if (_def("weight_kg") and _def("weight_kg") >= 20.0) else 70.0,
                step=0.1,
            )

        activity_opts = ["", "sedentary", "lightly active", "moderately active", "very active", "extremely active"]
        activity_level = st.selectbox(
            "Activity Level",
            activity_opts,
            index=activity_opts.index(_def("activity_level")) if _def("activity_level") in activity_opts else 0,
        )
        goal = st.text_input("Goal", value=_def("goal") or "", max_chars=200)
        health_conditions = st.text_area("Health Conditions & Notes", value=_def("health_conditions") or "", height=100)

        if height_cm and weight_kg and height_cm > 0 and weight_kg > 0:
            bmi_preview = weight_kg / ((height_cm / 100) ** 2)
            st.info(f"BMI preview: {bmi_preview:.1f}")

        col_s, col_c = st.columns(2)
        save = col_s.form_submit_button("Save", type="primary")
        cancel = col_c.form_submit_button("Cancel")

        if save:
            payload = {
                "age": int(age) if age else None,
                "gender": gender or None,
                "height_cm": int(height_cm) if height_cm else None,
                "weight_kg": float(weight_kg) if weight_kg else None,
                "activity_level": activity_level or None,
                "goal": goal.strip() or None,
                "health_conditions": health_conditions.strip() or None,
            }
            try:
                if mode == "create":
                    client.create_user_health_profile(user_id, payload)
                else:
                    client.update_user_health_profile(user_id, payload)
                st.success("Health saved")
                st.switch_page("pages/profile.py")
            except APIException as exc:
                st.error(f"Failed to save health profile: {exc.message}")

        if cancel:
            st.switch_page("pages/profile.py")


if __name__ == "__main__":
    main()