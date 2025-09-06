"""User profile page for NUGAMOTO frontend."""

from __future__ import annotations

from typing import Any

import streamlit as st

from frontend.utils.layout import render_sidebar
from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.clients.base import APIException
from frontend.clients.users_client import UsersClient
from frontend.clients.user_credentials_client import UserCredentialsClient
from frontend.clients.user_health_client import UserHealthClient


class ProfilePageController:
    def __init__(self) -> None:
        render_sidebar()
        self.users_client = UsersClient()
        self.creds_client = UserCredentialsClient()
        self.health_client = UserHealthClient()
        access = st.session_state.get("auth_access_token")
        refresh = st.session_state.get("auth_refresh_token")
        if access:
            self.users_client.set_tokens(access, refresh)
            self.creds_client.set_tokens(access, refresh)
            self.health_client.set_tokens(access, refresh)

    @staticmethod
    def _require_user_id() -> int | None:
        cu = st.session_state.get("current_user")
        if not isinstance(cu, dict) or cu.get("id") is None:
            st.warning("User context missing. Please login.")
            st.switch_page("pages/login.py")
            return None
        return int(cu["id"])


    @staticmethod
    def _metric_row(items: list[tuple[str, str]]) -> None:
        cols = st.columns(len(items))
        for col, (label, value) in zip(cols, items):
            col.metric(label, value)


    def _render_overview(self, user: dict[str, Any]) -> None:
        st.subheader("Overview")
        email = user.get("email", "unknown")
        name = user.get("name", "unknown")
        role_txt = "Admin" if bool(st.session_state.get("is_admin", False)) else "User"
        kitchen_name = st.session_state.get("selected_kitchen_name") or "–"
        kitchen_id = st.session_state.get("selected_kitchen_id") or "–"
        kitchen_role = st.session_state.get("selected_kitchen_role")
        kitchen_role_txt = str(kitchen_role).title() if kitchen_role else "–"

        self._metric_row(
            [
                ("Name", name),
                ("Email", email),
                ("Role", role_txt),
            ]
        )
        st.markdown("---")
        st.subheader("Kitchen Context")
        self._metric_row(
            [
                ("Kitchen", str(kitchen_name)),
                ("Kitchen ID", str(kitchen_id)),
                ("Your Role", kitchen_role_txt),
            ]
        )
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Dashboard"):
                st.switch_page("app.py")
        with c2:
            if st.button("Logout"):
                st.session_state.auth_access_token = None
                st.session_state.auth_refresh_token = None
                st.session_state.auth_email = None
                st.session_state.is_admin = False
                st.session_state.current_user = None
                st.success("Signed out.")
                st.rerun()


    def _render_credentials(self, user_id: int) -> None:
        st.subheader("Credentials")
        try:
            creds = self.creds_client.get_user_credentials(user_id)
            mode = "edit"
        except APIException:
            creds = None
            mode = "create"


        def _def(key: str) -> Any:
            return creds.get(key) if isinstance(creds, dict) else None


        with st.form("profile_credentials_form", clear_on_submit=False):
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
                try:
                    if mode == "create":
                        if not password:
                            st.error("Password required")
                            return
                        if password != confirm_password:
                            st.error("Passwords do not match")
                            return
                        payload["password_hash"] = password
                        self.creds_client.create_user_credentials(user_id, payload)
                        st.success("Credentials created")
                    else:
                        if new_password or confirm_new_password:
                            if not new_password:
                                st.error("Please provide the new password")
                                return
                            if new_password != confirm_new_password:
                                st.error("New passwords do not match")
                                return
                            payload["password_hash"] = new_password
                        self.creds_client.update_user_credentials(user_id, payload)
                        st.success("Credentials updated")
                    st.rerun()
                except APIException as exc:
                    st.error(f"Failed to save credentials: {exc.message}")

            if cancel_clicked:
                st.rerun()

        if creds:
            st.markdown("---")
            st.caption("Computed")
            full_name = creds.get("full_name")
            full_address = creds.get("full_address")
            c1, c2 = st.columns(2)
            c1.write(f"Full Name: {full_name or '–'}")
            if full_address:
                c2.write("Full Address:")
                st.text(full_address)


    def _render_health(self, user_id: int) -> None:
        st.subheader("Health")
        try:
            profile = self.health_client.get_user_health_profile(user_id)
            mode = "edit"
        except APIException:
            profile = None
            mode = "create"


        def _def(key: str) -> Any:
            return profile.get(key) if isinstance(profile, dict) else None


        with st.form("profile_health_form", clear_on_submit=False):
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

            health_conditions = st.text_area(
                "Health Conditions & Notes",
                value=_def("health_conditions") or "",
                height=100,
            )

            bmi_preview = None
            if height_cm and weight_kg and height_cm > 0 and weight_kg > 0:
                bmi_preview = weight_kg / ((height_cm / 100) ** 2)
                st.info(f"BMI preview: {bmi_preview:.1f}")

            col_save, col_cancel = st.columns(2)
            save_clicked = col_save.form_submit_button("Save", type="primary")
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if save_clicked:
                payload: dict[str, Any] = {
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
                        self.health_client.create_user_health_profile(user_id, payload)
                        st.success("Health profile created")
                    else:
                        self.health_client.update_user_health_profile(user_id, payload)
                        st.success("Health profile updated")
                    st.rerun()
                except APIException as exc:
                    st.error(f"Failed to save health profile: {exc.message}")

            if cancel_clicked:
                st.rerun()

        if profile:
            st.markdown("---")
            bmi = profile.get("bmi")
            is_complete = profile.get("is_complete", False)
            c1, c2 = st.columns(2)
            c1.metric("BMI", f"{bmi:.1f}" if isinstance(bmi, (int, float)) else "N/A")
            c2.metric("Complete", "Yes" if is_complete else "No")


    def render(self) -> None:
        st.title("Profile")
        user_id = self._require_user_id()
        if not user_id:
            return

        cu = st.session_state.get("current_user") or {}
        try:
            user = self.users_client.get_user(user_id) if hasattr(self.users_client, "get_user") else cu
        except Exception:
            user = cu

        tabs = st.tabs(["Overview", "Credentials", "Health"])
        with tabs[0]:
            self._render_overview(user)
        with tabs[1]:
            self._render_credentials(user_id)
        with tabs[2]:
            self._render_health(user_id)


def main() -> None:
    st.set_page_config(page_title="Profile - NUGAMOTO", page_icon="👤", layout="wide")
    ProfilePageController().render()


if __name__ == "__main__":
    main()