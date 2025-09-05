"""Login page for NUGAMOTO frontend."""

from __future__ import annotations

import base64
import json
from typing import Any

import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path
from frontend.utils.sidebar import render_sidebar

ensure_frontend_on_sys_path(__file__)

from frontend.clients.auth_client import AuthClient
from frontend.clients.base import APIException


class LoginController:
    def __init__(self) -> None:
        render_sidebar()
        self.client = AuthClient()
        self._init_auth_state()


    @staticmethod
    def _init_auth_state() -> None:
        defaults: dict[str, Any] = {
            "auth_access_token": None,
            "auth_refresh_token": None,
            "auth_email": None,
            "auth_inflight": False,
            "auth_next_page": None,
            "current_user": None,
            "selected_kitchen_id": None,
            "selected_kitchen_name": None,
            "is_admin": False,
        }
        for k, v in defaults.items():
            st.session_state.setdefault(k, v)


    @staticmethod
    def _is_authenticated() -> bool:
        return bool(st.session_state.get("auth_access_token"))


    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)


    def _extract_user_id_from_jwt(self, access_token: str) -> int | None:
        try:
            parts = access_token.split(".")
            if len(parts) != 3:
                return None
            payload_raw = self._base64url_decode(parts[1])
            payload = json.loads(payload_raw.decode("utf-8"))
            raw = payload.get("sub") or payload.get("user_id")
            if raw is None:
                return None
            return int(raw)
        except Exception:
            return None


    def _is_admin_from_jwt(self, access_token: str) -> bool:
        try:
            parts = access_token.split(".")
            if len(parts) != 3:
                return False
            payload_raw = self._base64url_decode(parts[1])
            payload = json.loads(payload_raw.decode("utf-8"))
            is_superadmin = bool(payload.get("is_superadmin"))
            is_admin = bool(payload.get("is_admin"))
            role = str(payload.get("role") or "").strip().lower()
            perms = payload.get("permissions") or []
            if isinstance(perms, str):
                perms = [perms]
            by_role = role in {"admin", "superadmin"}
            by_perm = "users:create" in {str(p).strip().lower() for p in perms}
            return bool(is_superadmin or is_admin or by_role or by_perm)
        except Exception:
            return False


    def _store_tokens_and_context(self, access: str, refresh: str | None, email: str) -> None:
        st.session_state.auth_access_token = access
        st.session_state.auth_refresh_token = refresh
        st.session_state.auth_email = email
        user_id = self._extract_user_id_from_jwt(access) or st.session_state.get("current_user", {}).get("id")
        if not isinstance(st.session_state.current_user, dict):
            st.session_state.current_user = {}
        st.session_state.current_user["email"] = email
        if user_id is not None:
            st.session_state.current_user["id"] = int(user_id)
        st.session_state.is_admin = self._is_admin_from_jwt(access)


    @staticmethod
    def _clear_tokens() -> None:
        st.session_state.auth_access_token = None
        st.session_state.auth_refresh_token = None
        st.session_state.auth_email = None
        st.session_state.current_user = None


    def _render_logged_in(self) -> None:
        st.success(f"Signed in as {st.session_state.auth_email}")
        uid = st.session_state.current_user.get("id") if isinstance(st.session_state.current_user, dict) else None
        kitchen_info = st.session_state.get("selected_kitchen_name") or st.session_state.get("selected_kitchen_id")
        st.caption(f"User ID: {uid or 'unknown'} | Kitchen: {kitchen_info or 'not selected'}")
        c1, c2, c3 = st.columns(3)
        if c1.button("Go to Dashboard"):
            st.switch_page("app.py")
        if c2.button("Open Kitchens"):
            st.switch_page("pages/kitchens.py")
        if c3.button("Logout", disabled=st.session_state.auth_inflight):
            try:
                st.session_state.auth_inflight = True
                self.client.set_tokens(st.session_state.auth_access_token, st.session_state.auth_refresh_token)
                with st.spinner("Signing out..."):
                    try:
                        self.client.logout()
                    except APIException:
                        pass
                self._clear_tokens()
                st.success("Signed out.")
                st.rerun()
            finally:
                st.session_state.auth_inflight = False


    def _render_login_form(self) -> None:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", value="", autocomplete="email")
            password = st.text_input("Password", type="password", value="", autocomplete="current-password")
            submit = st.form_submit_button("Login", disabled=st.session_state.auth_inflight, type="primary")
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password.")
                    return
                try:
                    st.session_state.auth_inflight = True
                    with st.spinner("Signing in..."):
                        tokens = self.client.login(email=email.strip(), password=password)
                    access = tokens.get("access_token")
                    refresh = tokens.get("refresh_token")
                    if not access:
                        st.error("No access token received.")
                        return
                    self._store_tokens_and_context(access, refresh, email.strip())
                    st.success("Login successful.")
                    st.switch_page("app.py")
                except APIException as exc:
                    st.error(f"Login failed: {exc.message}")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")
                finally:
                    st.session_state.auth_inflight = False


    def render(self) -> None:
        st.set_page_config(page_title="Login - NUGAMOTO", page_icon="🔐")
        st.title("🔐 Login")
        if self._is_authenticated():
            self._render_logged_in()
        else:
            self._render_login_form()


def main() -> None:
    LoginController().render()


if __name__ == "__main__":
    main()