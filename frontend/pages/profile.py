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
        return int(cu["id"])

    @staticmethod
    def _metric_row(items: list[tuple[str, str]]) -> None:
        cols = st.columns(len(items))
        for col, (label, value) in zip(cols, items):
            col.metric(label, value)


    @staticmethod
    def _addr_lines(creds: dict[str, Any] | None) -> list[str]:
        if not isinstance(creds, dict):
            return []
        lines: list[str] = []
        fn = creds.get("full_name")
        if fn:
            lines.append(str(fn))
        addr = creds.get("address")
        if addr:
            lines.append(str(addr))
        city_line = " ".join([p for p in [creds.get("postal_code"), creds.get("city")] if p])
        if city_line:
            lines.append(city_line)
        country = creds.get("country")
        if country:
            lines.append(str(country))
        return lines


    @staticmethod
    def _health_summary(profile: dict[str, Any] | None) -> dict[str, str]:
        if not isinstance(profile, dict):
            return {
                "Age": "–",
                "Gender": "–",
                "Height": "–",
                "Weight": "–",
                "BMI": "–",
                "Activity": "–",
                "Goal": "–",
            }
        bmi = profile.get("bmi")
        return {
            "Age": str(profile.get("age") or "–"),
            "Gender": str(profile.get("gender") or "–").title() if profile.get("gender") else "–",
            "Height": f"{int(profile['height_cm'])} cm" if profile.get("height_cm") else "–",
            "Weight": f"{float(profile['weight_kg']):.1f} kg" if profile.get("weight_kg") else "–",
            "BMI": f"{bmi:.1f}" if isinstance(bmi, (int, float)) else "–",
            "Activity": str(profile.get("activity_level") or "–").title() if profile.get("activity_level") else "–",
            "Goal": str(profile.get("goal") or "–"),
        }


    def _render_overview(self, user_id: int, user: dict[str, Any]) -> None:
        st.subheader("Overview")
        email = user.get("email", "unknown")
        name = user.get("name", "unknown")
        role_txt = "Admin" if bool(st.session_state.get("is_admin", False)) else "User"
        kitchen_name = st.session_state.get("selected_kitchen_name") or "–"
        kitchen_id = st.session_state.get("selected_kitchen_id") or "–"
        kitchen_role = st.session_state.get("selected_kitchen_role")
        kitchen_role_txt = str(kitchen_role).title() if kitchen_role else "–"

        self._metric_row([("Name", name), ("Email", email), ("Role", role_txt)])
        st.markdown("---")
        st.subheader("Kitchen Context")
        self._metric_row(
            [("Kitchen", str(kitchen_name)), ("Kitchen ID", str(kitchen_id)), ("Your Role", kitchen_role_txt)]
        )

        st.markdown("---")
        st.subheader("Lifestyle Summary")
        dt = user.get("diet_type") or "–"
        allergies = user.get("allergies") or "–"
        prefs = user.get("preferences") or "–"
        self._metric_row(
            [
                ("Diet", str(dt).replace("-", " ").title() if dt != "–" else "–"),
                ("Allergies", allergies),
                ("Preferences", prefs),
            ]
        )

        st.markdown("---")
        st.subheader("Health Summary")
        try:
            profile = self.health_client.get_user_health_profile(user_id)
        except APIException:
            profile = None
        hs = self._health_summary(profile)
        c1, c2, c3 = st.columns(3)
        c1.metric("Age", hs["Age"])
        c2.metric("Gender", hs["Gender"])
        c3.metric("BMI", hs["BMI"])
        c4, c5, c6 = st.columns(3)
        c4.metric("Height", hs["Height"])
        c5.metric("Weight", hs["Weight"])
        c6.metric("Activity", hs["Activity"])
        if hs["Goal"] and hs["Goal"] != "–":
            st.info(f"Goal: {hs['Goal']}")

        if st.button("Edit Health", key="btn_overview_edit_health"):
            st.switch_page("pages/profile_edit_health.py")
        if st.button("Dashboard", key="btn_overview_dashboard"):
            st.switch_page("app.py")
        if st.button("Logout", key="btn_overview_logout"):
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
        except APIException:
            creds = None

        if not creds:
            st.info("No credentials yet.")
            if st.button("Create Credentials", key="btn_creds_create", type="primary"):
                st.switch_page("pages/profile_edit_credentials.py")
            return

        lines = self._addr_lines(creds)
        if lines:
            st.text("\n".join(lines))
        phone = creds.get("phone")
        if phone:
            st.write(f"Phone: {phone}")
        if st.button("Edit Credentials", key="btn_creds_edit"):
            st.switch_page("pages/profile_edit_credentials.py")

    def _render_health(self, user_id: int) -> None:
        st.subheader("Health")
        try:
            profile = self.health_client.get_user_health_profile(user_id)
        except APIException:
            profile = None

        if not profile:
            st.info("No health profile yet.")
            if st.button("Create Health Profile", key="btn_health_create", type="primary"):
                st.switch_page("pages/profile_edit_health.py")
            return

        hs = self._health_summary(profile)
        c1, c2, c3 = st.columns(3)
        c1.metric("Age", hs["Age"])
        c2.metric("Gender", hs["Gender"])
        c3.metric("BMI", hs["BMI"])
        c4, c5, c6 = st.columns(3)
        c4.metric("Height", hs["Height"])
        c5.metric("Weight", hs["Weight"])
        c6.metric("Activity", hs["Activity"])
        if hs["Goal"] and hs["Goal"] != "–":
            st.info(f"Goal: {hs['Goal']}")
        st.write(profile.get("health_conditions") or "–")
        if st.button("Edit Health", key="btn_health_edit"):
            st.switch_page("pages/profile_edit_health.py")

        st.markdown("---")
        st.subheader("Lifestyle & Preferences")
        try:
            user = self.users_client.get_user(user_id)
        except Exception:
            user = st.session_state.get("current_user") or {}
        dt = user.get("diet_type") or "–"
        allergies = user.get("allergies") or "–"
        prefs = user.get("preferences") or "–"
        st.write(f"• Diet Type: {str(dt).replace('-', ' ').title() if dt != '–' else '–'}")
        st.write(f"• Allergies: {allergies}")
        st.write(f"• Preferences: {prefs}")
        if st.button("Edit User Profile", key="btn_health_edit_user"):
            st.switch_page("pages/profile_edit_user.py")

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
            self._render_overview(user_id, user)
        with tabs[1]:
            self._render_credentials(user_id)
        with tabs[2]:
            self._render_health(user_id)

def main() -> None:
    st.set_page_config(page_title="Profile - NUGAMOTO", page_icon="👤", layout="wide")
    ProfilePageController().render()


if __name__ == "__main__":
    main()