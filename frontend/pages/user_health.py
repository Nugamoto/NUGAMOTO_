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

from typing import Any

import pandas as pd
import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path
from frontend.utils.sidebar import render_sidebar

ensure_frontend_on_sys_path(__file__)

from frontend.clients import (
    UserHealthClient,
    UsersClient,
    APIException,
)



class UserHealthController:
    """Encapsulates all UI and API logic for the user health page.

    This controller keeps two datasets in session state:
    - health_rows_all: full list from the backend (ground truth)
    - health_rows: the current view (may be filtered by search or UI filters)

    The "Users available for new profiles" calculation must always use
    health_rows_all to avoid showing users as available simply because
    they were filtered out by the current view/search.
    """


    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        render_sidebar()
        self.health_client = UserHealthClient()
        self.users_client = UsersClient()
        # Tokens aus Session setzen (falls vorhanden)
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.health_client.set_tokens(access, refresh)
            self.users_client.set_tokens(access, refresh)
        self._init_state()

    @staticmethod
    def _init_state() -> None:
        """Initialize default values in Streamlit session state."""
        defaults: dict[str, Any] = {
            # Data (all vs. view)
            "health_rows_all": [],  # full dataset from API (ground truth)
            "health_rows": [],  # current view (search/filter applied)
            "health_rows_loaded": False,

            # Users master
            "users_master": [],

            # UI state
            "show_add": False,
            "show_edit": False,
            "show_details": False,
            "show_search": False,
            "row_for_edit": None,
            "row_for_details": None,
            "health_filter": "All",

            # Search state
            "is_search_active": False,
            "search_clear_requested": False,
        }
        for key, val in defaults.items():
            st.session_state.setdefault(key, val)

    # ----------------------------- data loading ---------------------- #
    def _load_master_data(self) -> None:
        """Load users into session state."""
        try:
            st.session_state.users_master = self.users_client.list_users(limit=1000)
        except APIException as exc:
            st.error(f"Failed to load users: {exc.message}")

    def _load_health_profiles(self, *, force: bool = False) -> list[dict[str, Any]]:
        """Fetch health profiles unless cached or force=True.

        On load, both health_rows_all and health_rows are updated.
        health_rows represents the current view and is reset to the full
        dataset when (re)loading from API.

        Args:
            force: If True, always reload from API.

        Returns:
            list[dict[str, Any]]: The current view rows (health_rows).
        """
        try:
            if not force and st.session_state.health_rows_loaded:
                return st.session_state.health_rows

            rows = self.health_client.get_all_health_profiles_summary(limit=1000)
            rows = sorted(rows, key=lambda x: x["user_id"])

            # Ground truth + reset current view
            st.session_state.health_rows_all = rows
            st.session_state.health_rows = rows.copy()

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

        Always uses the full dataset (health_rows_all) to determine which
        users already have profiles, independent of current search/filter.

        Returns:
            dict[str, int]: Mapping "Name (Email)" -> user_id for eligible users.
        """
        all_users = st.session_state.users_master
        full_profiles = st.session_state.health_rows_all or st.session_state.health_rows
        users_with_profiles = {p["user_id"] for p in full_profiles}

        return {
            f'{u["name"]} ({u["email"]})': u["id"]
            for u in all_users
            if u["id"] not in users_with_profiles
        }

    @staticmethod
    def _apply_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return rows filtered according to current selection.

        Args:
            rows: Current view rows (typically st.session_state.health_rows).

        Returns:
            list[dict[str, Any]]: Filtered rows.
        """
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
        """Format optional text for table display.

        Args:
            value: Optional value.

        Returns:
            str: Dash if missing, otherwise the value.
        """
        return value if value else "–"

    @staticmethod
    def _format_bmi(bmi: float | None) -> str:
        """Format BMI with category label.

        Args:
            bmi: BMI value or None.

        Returns:
            str: Formatted BMI with category, or dash if None.
        """
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
        """Resolve user email by ID from the master users list.

        Args:
            user_id: User identifier.
            users_list: Full list of users.

        Returns:
            str: Email address or a fallback label.
        """
        for user in users_list:
            if user["id"] == user_id:
                return user.get("email", f"user{user_id}@unknown")
        return f"user{user_id}@unknown"

    # ----------------------------- search form ----------------------- #
    def _render_search_form(self) -> None:
        """Render the Advanced Search form and apply results to view only.

        Notes:
            - Search updates st.session_state.health_rows (view) ONLY.
            - st.session_state.health_rows_all remains unchanged and is
              used as ground truth for availability calculations.
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
            if not value or not str(value).strip():
                return None
            try:
                return int(str(value).strip())
            except ValueError:
                st.warning("Min/Max Age must be an integer.")
                return None

        def _to_float(value: str | None) -> float | None:
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
                min_age_str = st.text_input("Min Age", value="", key="search_min_age_txt", placeholder="e.g. 30")
                max_age_str = st.text_input("Max Age", value="", key="search_max_age_txt", placeholder="e.g. 60")
                gender = st.selectbox("Gender", ["", "male", "female", "other"], key="search_gender")

            with col_right:
                activity_levels = [
                    "",
                    "sedentary",
                    "lightly active",
                    "moderately active",
                    "very active",
                    "extremely active",
                ]
                activity_level = st.selectbox("Activity Level", activity_levels, key="search_activity")
                min_bmi_str = st.text_input("Min BMI", value="", key="search_min_bmi_txt", placeholder="e.g. 18.5")
                max_bmi_str = st.text_input("Max BMI", value="", key="search_max_bmi_txt", placeholder="e.g. 30")

            col_search, col_clear, col_cancel = st.columns(3)
            search_clicked = col_search.form_submit_button("🔍 Search", type="primary")
            clear_clicked = col_clear.form_submit_button("Clear")
            cancel_clicked = col_cancel.form_submit_button("Cancel")

            if search_clicked:
                # Base search on the full dataset, not the current view
                st.session_state.health_rows_all or self._load_health_profiles(force=True)

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

                try:
                    # Use backend search for accuracy (keeps 'all' untouched)
                    results = self.health_client.search_health_profiles(**params)
                    results = sorted(results, key=lambda x: x["user_id"])
                    st.session_state.health_rows = results
                    st.session_state.is_search_active = True
                    st.session_state.health_filter = "All"
                    st.success(f"Found {len(results)} profiles matching criteria")
                    st.rerun()
                except APIException as exc:
                    st.error(f"Search failed: {exc.message}")

            if clear_clicked:
                st.session_state["search_clear_requested"] = True
                st.session_state.is_search_active = False
                # Reload full dataset and reset current view
                self._load_health_profiles(force=True)
                st.success("Search cleared")
                st.rerun()

            if cancel_clicked:
                st.session_state.show_search = False
                st.rerun()


    # ------------------------- table rendering ----------------------- #
    def render_table(self, rows: list[dict[str, Any]]) -> None:
        """Render health profiles rows and handle selection actions.

        Args:
            rows: The current view rows (typically st.session_state.health_rows).
        """
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

    # ----------------------------- CRUD helpers ---------------------- #
    def _save_health_profile(
            self,
            *,
            is_new: bool,
            user_id: int,
            payload: dict[str, Any],
    ) -> None:
        """Create or update a health profile and refresh the view.

        Args:
            is_new: Whether to create a new profile.
            user_id: Target user ID.
            payload: Data to send to the API.
        """
        try:
            if is_new:
                self.health_client.create_user_health_profile(user_id, payload)
            else:
                self.health_client.update_user_health_profile(user_id, payload)
            st.success("Health profile saved")
            st.session_state.show_add = False
            st.session_state.show_edit = False
            # Reload full dataset and reset view after changes
            self._load_health_profiles(force=True)
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
        """Render the Add/Edit Health Profile form.

        Args:
            is_new: Whether form is for creation.
            defaults: Existing record (for edit).
        """
        st.subheader("Add Health Profile" if is_new else "Edit Health Profile")

        def _def(key: str) -> Any:
            return defaults.get(key) if defaults else None

        with st.form("health_form", clear_on_submit=is_new):
            # User selection (new profiles only), based on full dataset
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
                    help="Only users without existing health profiles are shown",
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
                age = st.number_input(
                    "Age",
                    min_value=10,
                    max_value=120,
                    value=_def("age") or 25,
                    step=1,
                )
                gender_options = ["", "male", "female", "other"]
                gender = st.selectbox(
                    "Gender",
                    gender_options,
                    index=gender_options.index(_def("gender")) if _def("gender") in gender_options else 0,
                )

            with col2:
                height_cm = st.number_input(
                    "Height (cm)",
                    min_value=50,
                    max_value=300,
                    value=_def("height_cm") or 170,
                    step=1,
                )
                weight_kg = st.number_input(
                    "Weight (kg)",
                    min_value=20.0,
                    max_value=500.0,
                    value=_def("weight_kg") if (_def("weight_kg") and _def("weight_kg") >= 20.0) else 70.0,
                    step=0.1,
                )

            # Lifestyle & Goals
            st.subheader("Lifestyle & Goals")
            activity_levels = ["", "sedentary", "lightly active", "moderately active", "very active",
                               "extremely active"]
            activity_level = st.selectbox(
                "Activity Level",
                activity_levels,
                index=activity_levels.index(_def("activity_level")) if _def("activity_level") in activity_levels else 0,
            )
            goal = st.text_input("Health/Fitness Goal", value=_def("goal") or "", max_chars=200)

            # Health Information
            st.subheader("Health Information")
            health_conditions = st.text_area(
                "Health Conditions & Medical Notes",
                value=_def("health_conditions") or "",
                height=100,
                help="List any medical conditions, allergies, medications, or other health considerations",
            )

            # BMI Preview
            if height_cm and weight_kg and height_cm > 0 and weight_kg > 0:
                preview_bmi = weight_kg / ((height_cm / 100) ** 2)
                st.info(
                    f"🧮 Calculated BMI: {preview_bmi:.1f} - {self._format_bmi(preview_bmi).split('(')[1].rstrip(')')}")

            # Submit buttons
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

        # Load master users
        self._load_master_data()

        # Actions
        col_ref, col_add, col_search, col_info = st.columns([1, 1, 1, 3])
        if col_ref.button("🔄 Refresh"):
            self._load_health_profiles(force=True)

        # Availability must always be calculated from the full dataset
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

        # Filters
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
                # Reset to full dataset and view
                self._load_health_profiles(force=True)
                st.rerun()

        st.divider()

        # Advanced Search
        if st.session_state.show_search:
            self._render_search_form()
            st.divider()

        # Details
        if st.session_state.show_details and st.session_state.row_for_details:
            self._show_detailed_view(st.session_state.row_for_details)
            st.divider()

        # Forms
        if st.session_state.show_add:
            self._render_health_profile_form(is_new=True)
        if st.session_state.show_edit and st.session_state.row_for_edit:
            self._render_health_profile_form(is_new=False, defaults=st.session_state.row_for_edit)

        # Data retrieval and rendering
        if not st.session_state.health_rows_loaded:
            view_rows = self._load_health_profiles()
        else:
            view_rows = st.session_state.health_rows

        filtered_rows = self._apply_filter(view_rows)
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
