"""
User Health Management Page for NUGAMOTO Admin.

Features
--------
• View all user health profiles with complete backend data
• Add health profiles for users
• Edit user health profiles
• View detailed health information with BMI calculation
• Filter and search functionality
• Health analytics and insights
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
        UserHealthClient,
        UsersClient,
        APIException,
    )
except ImportError:  # fallback for "python …"
    from frontend.clients import (
        UserHealthClient,
        UsersClient,
        APIException,
    )


class UserHealthController:
    """Encapsulates all UI and API logic for the user health page."""


    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        self.health_client = UserHealthClient()
        self.users_client = UsersClient()
        self._init_state()


    @staticmethod
    def _init_state() -> None:
        defaults: dict[str, Any] = {
            "health_rows": [],
            "users_master": [],
            "show_add": False,
            "show_edit": False,
            "show_details": False,
            "show_search": False,
            "row_for_edit": None,
            "row_for_details": None,
            "health_filter": "All",
            # NEW: control fetching and search state
            "health_rows_loaded": False,
            "is_search_active": False,
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


    def _load_health_profiles(self, *, force: bool = False) -> list[dict[str, Any]]:
        """Fetch health profiles unless cached or force=True."""
        try:
            if not force and st.session_state.health_rows_loaded:
                return st.session_state.health_rows
            rows = self.health_client.get_all_health_profiles_summary(limit=1000)
            st.session_state.health_rows = sorted(rows, key=lambda x: x["user_id"])
            st.session_state.health_rows_loaded = True
            st.session_state.is_search_active = False
            return st.session_state.health_rows
        except APIException as exc:
            st.error(f"Failed to load health profiles: {exc.message}")
            return []


    # ----------------------------- helpers --------------------------- #

    @staticmethod
    def _get_users_without_health_profile() -> dict[str, int]:
        """Return users that do not yet have a health profile.

        This method reads the users and existing health profiles from
        Streamlit's session state and returns a mapping of display labels
        to user IDs for users without a profile.

        Returns:
            dict[str, int]: Mapping of "Name (Email)" to user ID for users
            who do not have an associated health profile yet.
        """
        all_users = st.session_state.users_master
        existing_profiles = st.session_state.health_rows
        users_with_profiles = {profile["user_id"] for profile in existing_profiles}

        available_users = {
            f'{user["name"]} ({user["email"]})': user["id"]
            for user in all_users
            if user["id"] not in users_with_profiles
        }
        return available_users


    @staticmethod
    def _apply_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return rows filtered according to current selection."""
        mode = st.session_state.get("health_filter", "All")
        if mode == "Complete Profiles":
            return [r for r in rows if r.get("is_complete", False)]
        if mode == "Incomplete Profiles":
            return [r for r in rows if not r.get("is_complete", True)]
        if mode == "With BMI":
            return [r for r in rows if r.get("bmi") is not None]
        if mode == "Male":
            return [r for r in rows if r.get("gender") == "male"]
        if mode == "Female":
            return [r for r in rows if r.get("gender") == "female"]
        if mode == "Very Active":
            return [r for r in rows if r.get("activity_level") == "very active"]
        return rows


    @staticmethod
    def _format_optional_field(value: str | None) -> str:
        if not value:
            return "–"
        return value


    @staticmethod
    def _format_bmi(bmi: float | None) -> str:
        if bmi is None:
            return "–"
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"
        return f"{bmi:.1f} ({category})"


    @staticmethod
    def _get_user_email_by_id(user_id: int, users_list: list[dict[str, Any]]) -> str:
        for user in users_list:
            if user["id"] == user_id:
                return user.get("email", f"user{user_id}@unknown")
        return f"user{user_id}@unknown"


    # ------------------------- table rendering ----------------------- #
    def render_table(self, rows: list[dict[str, Any]]) -> None:
        """Render health profiles rows and handle selection actions."""
        if not rows:
            st.info("No health profiles found.")
            return

        df = pd.DataFrame(
            {
                "User ID": [r["user_id"] for r in rows],
                "Email": [self._get_user_email_by_id(r["user_id"], st.session_state.users_master) for r in rows],
                "Age": [r.get("age", "–") for r in rows],
                "Gender": [self._format_optional_field(r.get("gender")) for r in rows],
                "BMI": [self._format_bmi(r.get("bmi")) for r in rows],
                "Activity Level": [self._format_optional_field(r.get("activity_level")) for r in rows],
                "Goal": [self._format_optional_field(r.get("goal")) for r in rows],
                "Complete": ["✅" if r.get("is_complete", False) else "❌" for r in rows],
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
            st.write(f"**{len(selected)} health profile(s) selected**")

            if len(selected) == 1:
                col_edit, col_view, col_close, _ = st.columns([1, 1, 1, 5])

                if col_edit.button("Edit Selected"):
                    try:
                        full_profile = self.health_client.get_user_health_profile(selected[0]["user_id"])
                        st.session_state.row_for_edit = full_profile
                        st.session_state.show_edit = True
                        st.session_state.show_details = False
                        st.rerun()
                    except APIException as exc:
                        st.error(f"Failed to load health profile: {exc.message}")

                if col_view.button("View Details"):
                    try:
                        full_profile = self.health_client.get_user_health_profile(selected[0]["user_id"])
                        st.session_state.row_for_details = full_profile
                        st.session_state.show_details = True
                        st.session_state.show_edit = False
                        st.rerun()
                    except APIException as exc:
                        st.error(f"Failed to load health profile: {exc.message}")

                if col_close.button("Close Details"):
                    st.session_state.show_details = False
                    st.session_state.row_for_details = None
                    st.rerun()
            else:
                st.info("Please select exactly one user to view details or edit.")


    # ----------------------------- detailed view ---------------------- #
    def _show_detailed_view(self, profile: dict[str, Any]) -> None:
        with st.expander("🏥 Complete Health Profile Details", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Basic Information")
                st.write(f"**Profile ID:** {profile.get('id', 'N/A')}")
                st.write(f"**User ID:** {profile.get('user_id', 'N/A')}")
                st.write(
                    f"**Email:** {self._get_user_email_by_id(profile.get('user_id', 0), st.session_state.users_master)}")
                st.write(f"**Age:** {profile.get('age', 'N/A')} years")
                st.write(f"**Gender:** {self._format_optional_field(profile.get('gender'))}")

                st.subheader("Physical Metrics")
                st.write(f"**Height:** {profile.get('height_cm', 'N/A')} cm")
                st.write(f"**Weight:** {profile.get('weight_kg', 'N/A')} kg")
                bmi = profile.get('bmi')
                st.write(f"**BMI:** {self._format_bmi(bmi)}")

            with col2:
                st.subheader("Lifestyle & Goals")
                st.write(f"**Activity Level:** {self._format_optional_field(profile.get('activity_level'))}")
                st.write(f"**Goal:** {self._format_optional_field(profile.get('goal'))}")

                st.subheader("Health Information")
                health_conditions = profile.get('health_conditions')
                if health_conditions:
                    st.write("**Health Conditions:**")
                    st.text_area("", value=health_conditions, disabled=True, height=80, key="health_view")
                else:
                    st.write("**Health Conditions:** None reported")

            st.subheader("Profile Status")
            col3, col4 = st.columns(2)
            with col3:
                is_complete = profile.get('is_complete', False)
                st.write(f"**Profile Complete:** {'✅ Yes' if is_complete else '❌ No'}")
                if not is_complete:
                    st.warning("Profile incomplete - missing essential data for AI recommendations")
            with col4:
                st.write(f"**Created:** {profile.get('created_at', 'N/A')}")
                st.write(f"**Updated:** {profile.get('updated_at', 'N/A')}")


    # ----------------------------- search form ----------------------- #
    def _render_search_form(self) -> None:
        """Render the Advanced Search form for health profiles.

        The form uses empty text inputs for numeric criteria to avoid implicit
        defaults. A "Clear" button resets the form and reloads the full dataset.
        A session flag is used to safely clear widget state before widgets are
        re-instantiated, avoiding Streamlit state errors.

        Workflow:
            - If "Clear" was requested previously, clear widget keys first.
            - Render inputs for age range, gender, activity, BMI range.
            - On "Search", build query parameters only from non-empty inputs,
              call the API, persist results, and rerun.
            - On "Clear", mark clear flag, reload full data, and rerun.
            - On "Cancel", hide the search form and rerun.

        Raises:
            Displays warnings for invalid numeric inputs.
        """
        st.subheader("🔍 Advanced Search")

        # Handle pending clear request before creating widgets
        if st.session_state.get("search_clear_requested"):
            for key in (
                    "search_min_age_txt",
                    "search_max_age_txt",
                    "search_gender",
                    "search_activity",
                    "search_min_bmi_txt",
                    "search_max_bmi_txt",
            ):
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state["search_clear_requested"] = False


        def _to_int(value: str | None) -> int | None:
            """Convert a string to int or return None if empty/invalid.

            Args:
                value: Raw string value from the text input.

            Returns:
                Optional integer parsed from the string.
            """
            if not value or not str(value).strip():
                return None
            try:
                return int(str(value).strip())
            except ValueError:
                st.warning("Min/Max Age must be an integer.")
                return None


        def _to_float(value: str | None) -> float | None:
            """Convert a string to float or return None if empty/invalid.

            Args:
                value: Raw string value from the text input.

            Returns:
                Optional float parsed from the string.
            """
            if not value or not str(value).strip():
                return None
            try:
                return float(str(value).strip())
            except ValueError:
                st.warning("Min/Max BMI must be a number.")
                return None


        with st.form("search_form"):
            col_left, col_right = st.columns(2)

            with col_left:
                min_age_str = st.text_input(
                    "Min Age",
                    value="",
                    key="search_min_age_txt",
                    placeholder="e.g. 30",
                )
                max_age_str = st.text_input(
                    "Max Age",
                    value="",
                    key="search_max_age_txt",
                    placeholder="e.g. 60",
                )
                gender = st.selectbox(
                    "Gender",
                    ["", "male", "female", "other"],
                    key="search_gender",
                )

            with col_right:
                activity_levels = [
                    "",
                    "sedentary",
                    "lightly active",
                    "moderately active",
                    "very active",
                    "extremely active",
                ]
                activity_level = st.selectbox(
                    "Activity Level",
                    activity_levels,
                    key="search_activity",
                )
                min_bmi_str = st.text_input(
                    "Min BMI",
                    value="",
                    key="search_min_bmi_txt",
                    placeholder="e.g. 18.5",
                )
                max_bmi_str = st.text_input(
                    "Max BMI",
                    value="",
                    key="search_max_bmi_txt",
                    placeholder="e.g. 30",
                )

            col_search, col_clear, col_cancel = st.columns(3)
            search_clicked = col_search.form_submit_button("🔍 Search", type="primary")
            clear_clicked = col_clear.form_submit_button("Clear")
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if search_clicked:
                try:
                    params: dict[str, Any] = {}

                    min_age = _to_int(min_age_str)
                    max_age = _to_int(max_age_str)
                    min_bmi = _to_float(min_bmi_str)
                    max_bmi = _to_float(max_bmi_str)

                    if min_age is not None:
                        params["min_age"] = min_age
                    if max_age is not None:
                        params["max_age"] = max_age
                    if gender:
                        params["gender"] = gender
                    if activity_level:
                        params["activity_level"] = activity_level
                    if min_bmi is not None:
                        params["min_bmi"] = min_bmi
                    if max_bmi is not None:
                        params["max_bmi"] = max_bmi

                    if not params:
                        st.warning("Please enter at least one search criterion.")
                        return

                    results = self.health_client.search_health_profiles(**params)
                    st.session_state.health_rows = results
                    st.session_state.health_rows_loaded = True
                    st.session_state.is_search_active = True
                    st.session_state.health_filter = "All"
                    st.success(f"Found {len(results)} profiles matching criteria")
                    st.rerun()
                except APIException as exc:
                    st.error(f"Search failed: {exc.message}")

            if clear_clicked:
                # Defer widget state reset until next render cycle
                st.session_state["search_clear_requested"] = True
                st.session_state.is_search_active = False
                self._load_health_profiles(force=True)
                st.success("Search cleared")
                st.rerun()

            if cancel_clicked:
                st.session_state.show_search = False
                st.rerun()


    # ----------------------------- CRUD helpers ---------------------- #
    def _save_health_profile(
            self,
            *,
            is_new: bool,
            user_id: int,
            payload: dict[str, Any],
    ) -> None:
        try:
            if is_new:
                self.health_client.create_user_health_profile(user_id, payload)
            else:
                self.health_client.update_user_health_profile(user_id, payload)
            st.success("Health profile saved")
            st.session_state.show_add = False
            st.session_state.show_edit = False
            st.rerun()
        except APIException as exc:
            st.error(f"API error: {exc.message}")


    # ------------------------- add/edit form ------------------------- #
    def _render_health_profile_form(
            self,
            *,
            is_new: bool,
            defaults: dict[str, Any] | None = None,
    ) -> None:
        title = "Add Health Profile" if is_new else "Edit Health Profile"
        st.subheader(f"🏥 {title}")


        def _def(key: str) -> Any:
            return defaults.get(key) if defaults else None


        with st.form("health_form", clear_on_submit=is_new):
            # User Selection (only for new profiles)
            if is_new:
                available_users = self._get_users_without_health_profile()
                if not available_users:
                    st.warning("⚠️ All users already have health profiles!")
                    st.info("Create new users first or edit existing health profiles.")
                    close_clicked = st.form_submit_button("Close", type="secondary")
                    if close_clicked:
                        st.session_state.show_add = False
                        st.rerun()
                    return

                user_sel = st.selectbox(
                    "User *",
                    list(available_users.keys()),
                    help="Only users without existing health profiles are shown"
                )
                selected_user_id = available_users[user_sel]
            else:
                user_email = self._get_user_email_by_id(_def("user_id"), st.session_state.users_master)
                st.text_input("User", value=f"User {_def('user_id')} ({user_email})", disabled=True)
                selected_user_id = _def("user_id")

            # Basic Information
            st.subheader("Basic Information")
            col1, col2 = st.columns(2)
            with col1:
                age_default = _def("age") if _def("age") else 25
                age = st.number_input("Age", min_value=10, max_value=120, value=age_default, step=1)
                gender_options = ["", "male", "female", "other"]
                gender_idx = gender_options.index(_def("gender")) if _def("gender") in gender_options else 0
                gender = st.selectbox("Gender", gender_options, index=gender_idx)

            with col2:
                height_default = _def("height_cm") if _def("height_cm") else 170
                height_cm = st.number_input("Height (cm)", min_value=50, max_value=300, value=height_default, step=1)
                weight_kg_default = _def("weight_kg") if _def("weight_kg") and _def("weight_kg") >= 20.0 else 70.0
                weight_kg = st.number_input("Weight (kg)", min_value=20.0, max_value=500.0, value=weight_kg_default,
                                            step=0.1)

            # Activity & Goals
            st.subheader("Lifestyle & Goals")
            activity_levels = ["", "sedentary", "lightly active", "moderately active", "very active",
                               "extremely active"]
            activity_idx = activity_levels.index(_def("activity_level")) if _def(
                "activity_level") in activity_levels else 0
            activity_level = st.selectbox("Activity Level", activity_levels, index=activity_idx)
            goal = st.text_input("Health/Fitness Goal", value=_def("goal") or "", max_chars=200)

            # Health Conditions
            st.subheader("Health Information")
            health_conditions = st.text_area(
                "Health Conditions & Medical Notes",
                value=_def("health_conditions") or "",
                height=100,
                help="List any medical conditions, allergies, medications, or other health considerations"
            )

            # BMI Preview
            if height_cm and weight_kg and height_cm > 0 and weight_kg > 0:
                bmi = weight_kg / ((height_cm / 100) ** 2)
                st.info(f"🧮 **Calculated BMI:** {bmi:.1f} - {self._format_bmi(bmi).split('(')[1].rstrip(')')}")

            col_save, col_cancel = st.columns(2)
            save_clicked = col_save.form_submit_button("💾 Save", type="primary")
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if save_clicked:
                payload: dict[str, Any] = {
                    "age": age if age > 0 else None,
                    "gender": gender if gender else None,
                    "height_cm": height_cm if height_cm > 0 else None,
                    "weight_kg": weight_kg if weight_kg > 0 else None,
                    "activity_level": activity_level if activity_level else None,
                    "health_conditions": health_conditions if health_conditions.strip() else None,
                    "goal": goal if goal.strip() else None,
                }
                self._save_health_profile(
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
        """Main page renderer."""
        st.title("🏥 User Health Profiles Management")

        # Load master data first
        self._load_master_data()

        # Actions
        col_ref, col_add, col_search, col_info = st.columns([1, 1, 1, 3])
        if col_ref.button("🔄 Refresh"):
            self._load_health_profiles(force=True)

        available_users_count = len(self._get_users_without_health_profile())
        if col_add.button("➕ Add Profile", disabled=available_users_count == 0):
            st.session_state.show_add = True

        if col_search.button("🔍 Advanced Search"):
            st.session_state.show_search = not st.session_state.show_search
            st.rerun()

        if available_users_count == 0:
            col_info.info("ℹ️ All users have health profiles")
        else:
            col_info.info(f"ℹ️ {available_users_count} users available for new profiles")

        # Filters row
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            selected_mode = st.selectbox(
                "Filter",
                ("All", "Complete Profiles", "Incomplete Profiles", "With BMI", "Male", "Female", "Very Active"),
                index=("All", "Complete Profiles", "Incomplete Profiles", "With BMI", "Male", "Female",
                       "Very Active").index(
                    st.session_state.health_filter
                ),
                key="health_filter_select",
            )
        with col_f2:
            if st.button("Apply Filter"):
                st.session_state.health_filter = selected_mode
                st.rerun()
        with col_f3:
            if st.button("Clear Filter"):
                st.session_state.health_filter = "All"
                # Reset search state and reload full dataset
                self._load_health_profiles(force=True)
                st.rerun()

        st.divider()

        # Search form
        if st.session_state.show_search:
            self._render_search_form()
            st.divider()

        # Details view
        if st.session_state.show_details and st.session_state.row_for_details:
            self._show_detailed_view(st.session_state.row_for_details)
            st.divider()

        # Forms
        if st.session_state.show_add:
            self._render_health_profile_form(is_new=True)

        if st.session_state.show_edit and st.session_state.row_for_edit:
            self._render_health_profile_form(is_new=False, defaults=st.session_state.row_for_edit)

        # Data retrieval: respect cached rows and searches
        if not st.session_state.health_rows_loaded:
            all_rows = self._load_health_profiles()
        else:
            all_rows = st.session_state.health_rows

        filtered_rows = self._apply_filter(all_rows)
        self.render_table(filtered_rows)

        # Analytics
        if filtered_rows:
            st.subheader("📊 Health Analytics Summary")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                complete_profiles = len([r for r in filtered_rows if r.get("is_complete", False)])
                st.metric("Complete Profiles", f"{complete_profiles}/{len(filtered_rows)}")

            with col2:
                ages = [r.get("age") for r in filtered_rows if r.get("age") is not None]
                avg_age = (sum(ages) / len(ages)) if ages else None
                st.metric("Average Age", f"{avg_age:.1f}" if avg_age else "N/A")

            with col3:
                bmis = [r.get("bmi") for r in filtered_rows if r.get("bmi") is not None]
                avg_bmi = (sum(bmis) / len(bmis)) if bmis else None
                st.metric("Average BMI", f"{avg_bmi:.1f}" if avg_bmi else "N/A")

            with col4:
                active_users = len(
                    [r for r in filtered_rows if r.get("activity_level") in ["very active", "extremely active"]])
                st.metric("Very/Extremely Active", f"{active_users}/{len(filtered_rows)}")


# ----------------------------------------------------------------------
# Page entry point
# ----------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="User Health - NUGAMOTO", page_icon="🏥")
    UserHealthController().render()


if __name__ == "__main__":
    main()
