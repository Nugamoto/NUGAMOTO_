"""Login page for NUGAMOTO frontend."""

from __future__ import annotations

import base64
import json
import os
import sys
from typing import Any

import streamlit as st

# Add frontend to path for runtime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Direct imports for IDE resolution
try:
    from clients.auth_client import AuthClient
    from clients.base import APIException
except ImportError:
    from frontend.clients.auth_client import AuthClient
    from frontend.clients.base import APIException


def _init_auth_state() -> None:
    """Initialize authentication-related session state."""
    defaults: dict[str, Any] = {
        "auth_access_token": None,
        "auth_refresh_token": None,
        "auth_email": None,
        "auth_inflight": False,
        "auth_next_page": None,
        "current_user": None,  # dict with at least {"id": int, "email": str}
        "selected_kitchen_id": None,  # int
        "selected_kitchen_name": None,  # str
    }
    for key, val in defaults.items():
        st.session_state.setdefault(key, val)


def _is_authenticated() -> bool:
    """Return True if an access token is present."""
    return bool(st.session_state.get("auth_access_token"))


def _base64url_decode(data: str) -> bytes:
    """Decode base64url without padding."""
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _extract_user_id_from_jwt(access_token: str) -> int | None:
    """Extract user_id from JWT payload without verification (frontend convenience)."""
    try:
        parts = access_token.split(".")
        if len(parts) != 3:
            return None
        payload_raw = _base64url_decode(parts[1])
        payload = json.loads(payload_raw.decode("utf-8"))
        raw = payload.get("sub") or payload.get("user_id")
        if raw is None:
            return None
        return int(raw)
    except Exception:
        return None


def _store_tokens_and_context(access: str, refresh: str | None, email: str) -> None:
    """Store tokens and derive user context from access token."""
    st.session_state.auth_access_token = access
    st.session_state.auth_refresh_token = refresh
    st.session_state.auth_email = email

    # Ensure current_user exists and contains id + email
    user_id = _extract_user_id_from_jwt(access) or st.session_state.get("current_user", {}).get("id")
    if not isinstance(st.session_state.current_user, dict):
        st.session_state.current_user = {}
    st.session_state.current_user["email"] = email
    if user_id is not None:
        st.session_state.current_user["id"] = int(user_id)


def _clear_tokens() -> None:
    """Clear tokens from session state."""
    st.session_state.auth_access_token = None
    st.session_state.auth_refresh_token = None
    st.session_state.auth_email = None
    st.session_state.current_user = None
    # Keep selected_kitchen_id if you want persistence across logouts, otherwise clear it too:
    # st.session_state.selected_kitchen_id = None
    # st.session_state.selected_kitchen_name = None


def main() -> None:
    """Render a robust login/logout page with clear UX."""
    st.set_page_config(page_title="Login - NUGAMOTO", page_icon="🔐")
    st.title("🔐 Login")

    _init_auth_state()
    client = AuthClient()

    # Logged-in view
    if _is_authenticated():
        st.success(f"Signed in as {st.session_state.auth_email}")

        # Quick context summary
        user_id = st.session_state.current_user.get("id") if isinstance(st.session_state.current_user, dict) else None
        kitchen_info = st.session_state.get("selected_kitchen_name") or st.session_state.get("selected_kitchen_id")
        st.caption(f"User ID: {user_id or 'unknown'} | Kitchen: {kitchen_info or 'not selected'}")

        col1, col2, col3 = st.columns(3)
        if col1.button("Go to Dashboard"):
            st.switch_page("app.py")
        if col2.button("Open Kitchens"):
            st.switch_page("pages/kitchens.py")
        if col3.button("Logout", disabled=st.session_state.auth_inflight):
            try:
                st.session_state.auth_inflight = True
                client.set_tokens(
                    st.session_state.auth_access_token,
                    st.session_state.auth_refresh_token,
                )
                with st.spinner("Signing out..."):
                    try:
                        client.logout()
                    except APIException:
                        pass
                _clear_tokens()
                st.success("Signed out.")
                st.rerun()
            finally:
                st.session_state.auth_inflight = False
        return

    # Login form
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email", value="", autocomplete="email")
        password = st.text_input("Password", type="password", value="", autocomplete="current-password")

        submit = st.form_submit_button(
            "Login",
            disabled=st.session_state.auth_inflight,
            type="primary",
        )

        if submit:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                try:
                    st.session_state.auth_inflight = True
                    with st.spinner("Signing in..."):
                        tokens = client.login(email=email.strip(), password=password)
                    access = tokens.get("access_token")
                    refresh = tokens.get("refresh_token")

                    if not access:
                        st.error("No access token received.")
                    else:
                        _store_tokens_and_context(access, refresh, email.strip())
                        st.success("Login successful.")
                        # Always go to the app; do not redirect to Kitchens automatically
                        st.switch_page("app.py")
                except APIException as exc:
                    st.error(f"Login failed: {exc.message}")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")
                finally:
                    st.session_state.auth_inflight = False


if __name__ == "__main__":
    main()