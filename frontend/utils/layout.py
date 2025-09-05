from __future__ import annotations

import os

import streamlit as st

from frontend.clients.base import APIException
from frontend.clients.kitchens_client import KitchensClient


def hide_native_pages_nav() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }
        .topbar {
            width: 100%;
            display: flex; align-items: center; justify-content: space-between;
            padding: 8px 16px; border-bottom: 1px solid rgba(255,255,255,0.1);
            margin: -1rem -1rem 0.25rem -1rem; box-sizing: border-box;
        }
        .pill {
            padding: 4px 8px; border-radius: 999px; font-size: 0.85rem;
            border: 1px solid rgba(255,255,255,0.15); opacity: 0.95;
            white-space: nowrap;
        }
        .label {
            opacity: 0.8; font-size: 0.9rem; margin-right: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _logo_path() -> str:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(project_root, "utils", "NUGAMOTO_logo.png")


def _perform_logout() -> None:
    st.session_state.auth_access_token = None
    st.session_state.auth_refresh_token = None
    st.session_state.auth_email = None
    st.session_state.is_admin = False
    st.session_state.current_user = None
    st.session_state._layout_needs_rerun = True


def _load_kitchens_for_user() -> list[dict]:
    user = st.session_state.get("current_user") or {}
    user_id = user.get("id")
    if not user_id:
        return []

    client = KitchensClient()
    access = st.session_state.get("auth_access_token")
    refresh = st.session_state.get("auth_refresh_token")
    if access:
        client.set_tokens(access, refresh)

    try:
        all_k = client.list_kitchens(limit=1000) or []
        rows: list[dict] = []
        for k in all_k:
            kid = k.get("id")
            nm = k.get("name", f"Kitchen {kid}")
            if not kid:
                continue
            try:
                details = client.get_kitchen(kid)
                role = None
                for key in ("users", "user_kitchens", "members"):
                    lst = details.get(key) or []
                    for it in lst:
                        if isinstance(it, dict):
                            if it.get("id") == user_id and it.get("role"):
                                role = it.get("role")
                                break
                            if it.get("user_id") == user_id and it.get("role"):
                                role = it.get("role")
                                break
                            if isinstance(it.get("user"), dict) and it["user"].get("id") == user_id and it.get("role"):
                                role = it.get("role")
                                break
                    if role:
                        break
                if role:
                    rows.append({"id": kid, "name": nm, "role": role})
            except APIException:
                continue
        rows.sort(key=lambda r: str(r.get("name", "")).lower())
        return rows
    except APIException:
        return []


def _render_topbar() -> None:
    hide_native_pages_nav()

    email = st.session_state.get("auth_email")
    is_admin = bool(st.session_state.get("is_admin", False))

    with st.container():
        st.markdown('<div class="topbar">', unsafe_allow_html=True)
        left, right = st.columns([7, 5], vertical_alignment="center")

        with left:
            l1, l2 = st.columns([2, 10], vertical_alignment="center")
            with l1:
                if email:
                    st.markdown('<span class="label">Kitchen:</span>', unsafe_allow_html=True)
            with l2:
                if email:
                    kitchens = _load_kitchens_for_user()
                    if kitchens:
                        labels = [f"{k['name']} ({k['role']})" for k in kitchens]
                        default_idx = 0
                        if st.session_state.get("selected_kitchen_id"):
                            for i, k in enumerate(kitchens):
                                if k["id"] == st.session_state["selected_kitchen_id"]:
                                    default_idx = i
                                    break
                        sel = st.selectbox(
                            "Kitchen",
                            options=range(len(labels)),
                            index=default_idx,
                            format_func=lambda i: labels[i],
                            label_visibility="collapsed",
                            key="__topbar_kitchen_select__",
                        )
                        chosen = kitchens[sel]
                        st.session_state.selected_kitchen_id = chosen["id"]
                        st.session_state.selected_kitchen_name = chosen["name"]
                        st.session_state.selected_kitchen_role = chosen["role"]

        with right:
            r1, r2, r3 = st.columns([6, 2, 2], vertical_alignment="center")
            with r1:
                if email:
                    role_txt = "Admin" if is_admin else "User"
                    st.markdown(f'<span class="pill">👤 {email} · {role_txt}</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pill">Not signed in</span>', unsafe_allow_html=True)
            with r2:
                st.button(
                    "Profile",
                    key="tb_profile_btn",
                    on_click=lambda: st.session_state.update(_nav_target="pages/profile.py"),
                )
            with r3:
                if email:
                    if st.button("Logout", key="tb_logout_btn"):
                        _perform_logout()
                else:
                    st.button(
                        "Login",
                        key="tb_login_btn",
                        on_click=lambda: st.session_state.update(_nav_target="pages/login.py"),
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.pop("_layout_needs_rerun", False):
        st.rerun()

    nav_target = st.session_state.pop("_nav_target", None)
    if nav_target:
        st.switch_page(nav_target)


def render_sidebar() -> None:
    _render_topbar()

    # responsive logo (fills sidebar width) and acts as dashboard button
    st.sidebar.button(
        "",
        key="sb_logo_btn",
        use_container_width=True,
        on_click=lambda: st.session_state.update(_nav_target="app.py"),
    )
    st.sidebar.image(_logo_path(), use_container_width=True)
    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")

    items = [
        ("🏠 Dashboard", "app.py"),
        ("🤖 AI Recipes", "pages/ai_recipes.py"),
        ("📖 Recipes", "pages/recipes.py"),
        ("📦 Inventory Items", "pages/inventory_items.py"),
        ("🗄️ Storage Locations", "pages/storage_locations.py"),
        ("🥬 Food Items", "pages/food_items.py"),
        ("🍽️ Kitchens", "pages/kitchens.py"),
        ("⚙️ Units", "pages/units.py"),
        ("👤 Users", "pages/users.py"),
        ("🔐 User Credentials", "pages/user_credentials.py"),
        ("🏥 User Health", "pages/user_health.py"),
    ]

    for label, target in items:
        st.sidebar.button(
            label,
            key=f"nav_{label}",
            use_container_width=True,
            on_click=lambda t=target: st.session_state.update(_nav_target=t),
        )

    st.sidebar.markdown("---")

    nav_target = st.session_state.pop("_nav_target", None)
    if nav_target:
        st.switch_page(nav_target)
