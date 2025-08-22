from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

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
    defaults: Dict[str, Any] = {
        "auth_access_token": None,
        "auth_refresh_token": None,
        "auth_email": None,
        "auth_inflight": False,
        "auth_next_page": None,
        "current_user": None,  # Für Kompatibilität mit app.py
    }
    for key, val in defaults.items():
        st.session_state.setdefault(key, val)


def _is_authenticated() -> bool:
    """Return True if an access token is present."""
    return bool(st.session_state.get("auth_access_token"))


def _store_tokens(access: str, refresh: Optional[str], email: str) -> None:
    """Store tokens in session state."""
    st.session_state.auth_access_token = access
    st.session_state.auth_refresh_token = refresh
    st.session_state.auth_email = email
    # Set current_user for app.py compatibility
    st.session_state.current_user = {"email": email, "name": email}


def _clear_tokens() -> None:
    """Clear tokens from session state."""
    st.session_state.auth_access_token = None
    st.session_state.auth_refresh_token = None
    st.session_state.auth_email = None
    st.session_state.current_user = None


def main() -> None:
    """Render a robust login/logout page with clear UX."""
    st.set_page_config(page_title="Login - NUGAMOTO", page_icon="🔐")
    st.title("🔐 Login")

    _init_auth_state()
    client = AuthClient()

    # Logged-in view
    if _is_authenticated():
        st.success(f"Signed in as {st.session_state.auth_email}")
        col1, _ = st.columns(2)
        if col1.button("Logout", disabled=st.session_state.auth_inflight):
            try:
                st.session_state.auth_inflight = True
                client.set_tokens(
                    st.session_state.auth_access_token,
                    st.session_state.auth_refresh_token,
                )
                # Stateless logout; server call optional
                with st.spinner("Signing out..."):
                    try:
                        client.logout()
                    except APIException:
                        # Ignore server-side result; we clear client state regardless
                        pass
                _clear_tokens()
                st.success("Signed out.")
                st.rerun()
            finally:
                st.session_state.auth_inflight = False

        # Redirect to main app if logged in
        if st.button("Go to Dashboard"):
            st.switch_page("app.py")
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
                        _store_tokens(access, refresh, email.strip())
                        st.success("Login successful.")
                        # Set selected kitchen for testing
                        st.session_state.selected_kitchen_id = 1
                        st.session_state.selected_kitchen_name = "Test Kitchen"
                        # Optional: redirect to main app
                        st.rerun()
                except APIException as exc:
                    st.error(f"Login failed: {exc.message}")
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")
                finally:
                    st.session_state.auth_inflight = False


if __name__ == "__main__":
    main()