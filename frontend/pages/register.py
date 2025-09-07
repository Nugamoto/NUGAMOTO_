"""Registration page for NUGAMOTO frontend."""

from __future__ import annotations

import base64
import json
import re
from typing import Any

import streamlit as st

from frontend.utils.layout import render_sidebar
from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.clients.auth_client import AuthClient
from frontend.clients.base import APIException

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterController:
    """Encapsulates UI and API logic for user registration."""

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
            "current_user": None,
            "is_admin": False,
            "selected_kitchen_id": None,
            "selected_kitchen_name": None,
        }
        for k, v in defaults.items():
            st.session_state.setdefault(k, v)


    # ----- token helpers -----
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
            return int(raw) if raw is not None else None
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
        if not isinstance(st.session_state.current_user, dict):
            st.session_state.current_user = {}
        st.session_state.current_user["email"] = email
        user_id = self._extract_user_id_from_jwt(access)
        if user_id is not None:
            st.session_state.current_user["id"] = int(user_id)
        st.session_state.is_admin = self._is_admin_from_jwt(access)


    # ----- validation helpers -----
    @staticmethod
    def _password_checks(password: str, confirm: str) -> dict[str, bool]:
        """Return rule evaluation for password UI and validation."""
        return {
            "len": bool(password) and len(password) >= 8,
            "match": bool(password) and (password == confirm),
        }


    @staticmethod
    def _password_help_ui(checks: dict[str, bool]) -> None:
        """Render a compact checklist for password requirements."""
        ok = "✅"
        bad = "❌"
        st.caption(
            f"{ok if checks['len'] else bad} At least 8 characters"
            "   •   "
            f"{ok if checks['match'] else bad} Passwords match"
        )


    @staticmethod
    def _validate_inputs(name: str, email: str, password: str, confirm: str) -> tuple[bool, str | None]:
        """Validate form inputs; return (is_valid, user_message)."""
        if not name or not name.strip():
            return False, "Please enter your name."
        if not email or not EMAIL_RE.match(email.strip()):
            return False, "Please enter a valid email address."
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if password != confirm:
            return False, "Passwords do not match."
        return True, None


    @staticmethod
    def _friendly_api_error(status: int | None, message: str | None, raw: Any = None) -> str:
        """Map backend errors to user-friendly messages."""
        msg = (message or "").lower()
        if status in (400, 409) and "already" in msg and "email" in msg:
            return "This email is already registered. Try logging in instead."
        if status in (400, 422):
            if "password" in msg and ("short" in msg or "length" in msg or "8" in msg):
                return "Your password is too short. It must have at least 8 characters."
            if "email" in msg and ("invalid" in msg or "value is not a valid" in msg):
                return "The email address appears to be invalid."
        # Fallback
        return "Registration failed. Please check your inputs and try again."

    # ----- UI -----
    def _render_form(self) -> None:
        st.set_page_config(page_title="Register - NUGAMOTO", page_icon="🆕")
        st.title("🆕 Sign Up")

        with st.form("register_form", clear_on_submit=False):
            col_name, col_email = st.columns([1, 1])
            with col_name:
                name = st.text_input("Name", value="", placeholder="Your display name")
            with col_email:
                email = st.text_input("Email", value="", autocomplete="email", placeholder="you@example.com")

            col_pw1, col_pw2 = st.columns([1, 1])
            with col_pw1:
                password = st.text_input("Password", type="password", autocomplete="new-password")
            with col_pw2:
                confirm = st.text_input("Confirm Password", type="password", autocomplete="new-password")

            # Live-Feedback unter den Feldern
            self._password_help_ui(self._password_checks(password, confirm))

            col_submit, col_cancel = st.columns([1, 1])
            submitted = col_submit.form_submit_button(
                "Create Account",
                type="primary",
                disabled=st.session_state.auth_inflight,
            )
            cancelled = col_cancel.form_submit_button("Back to Login")

            if submitted:
                valid, user_msg = self._validate_inputs(name, email, password, confirm)
                if not valid:
                    st.error(user_msg)
                    return
                try:
                    st.session_state.auth_inflight = True
                    with st.spinner("Creating your account..."):
                        tokens = self.client.register(
                            name=name.strip(),
                            email=email.strip(),
                            password=password,
                        )
                    access = tokens.get("access_token")
                    refresh = tokens.get("refresh_token")
                    if not access:
                        st.error("Registration succeeded but no access token received.")
                        return
                    self._store_tokens_and_context(access, refresh, email.strip())
                    st.success("Welcome! Your account has been created.")
                    st.switch_page("app.py")
                except APIException as exc:
                    status = getattr(exc, "status_code", None)
                    msg = getattr(exc, "message", "") or str(exc)
                    raw = getattr(exc, "details", None) or getattr(exc, "response_text", None)
                    st.error(self._friendly_api_error(status, msg, raw))
                    # Optional: technische Details aufklappbar
                    if raw:
                        with st.expander("Technical details", expanded=False):
                            st.code(str(raw))
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")
                finally:
                    st.session_state.auth_inflight = False

            if cancelled:
                st.switch_page("pages/login.py")

        st.caption("By signing up you agree to our terms and privacy policy.")

    def render(self) -> None:
        self._render_form()


def main() -> None:
    RegisterController().render()


if __name__ == "__main__":
    main()