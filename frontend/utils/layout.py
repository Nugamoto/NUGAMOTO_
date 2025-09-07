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
            flex-wrap: wrap; row-gap: 6px;
        }
        .pill {
            padding: 4px 8px; border-radius: 999px; font-size: 0.85rem;
            border: 1px solid rgba(255,255,255,0.15); opacity: 0.95;
            white-space: nowrap;
            max-width: 100%; overflow: hidden; text-overflow: ellipsis;
        }
        .label {
            opacity: 0.85; font-size: 0.9rem; margin-right: 4px;
            white-space: nowrap;
        }
        /* Make Streamlit buttons more compact and prevent wrapping */
        .stButton > button {
            white-space: nowrap;
            padding: 4px 10px;
            line-height: 1.1;
            font-size: 0.9rem;
        }
        /* Give the buttons some breathing room on narrow screens */
        @media (max-width: 820px) {
          .pill { max-width: 60vw; }
        }
        @media (max-width: 520px) {
          .pill { display: none; }
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
        left, right = st.columns([8, 4], vertical_alignment="center")

        with left:
            if email:
                c1, c2 = st.columns([2, 10], vertical_alignment="center")
                with c1:
                    st.markdown('<span class="label">Kitchen:</span>', unsafe_allow_html=True)
                with c2:
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
            r1, r2, r3 = st.columns([5, 2, 2], vertical_alignment="center")
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
                    use_container_width=True,
                )
            with r3:
                if email:
                    if st.button("Logout", key="tb_logout_btn", use_container_width=True):
                        _perform_logout()
                else:
                    st.button(
                        "Login",
                        key="tb_login_btn",
                        on_click=lambda: st.session_state.update(_nav_target="pages/login.py"),
                        use_container_width=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar() -> None:
    _render_topbar()

    st.sidebar.image(_logo_path(), use_container_width=True, output_format="PNG", clamp=True, caption=None,
                     channels="RGB")
    st.sidebar.page_link("app.py", label="🏠 Dashboard", icon=None)
    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")

    current_user = st.session_state.get("current_user") or {}
    role = str(current_user.get("role", "") or "").lower()
    is_superadmin = bool(getattr(st.session_state, "is_superadmin", False)) or role == "superadmin"

    core_items = [
        ("🤖 AI Recipes", "pages/ai_recipes.py"),
        ("📖 Recipes", "pages/recipes.py"),
        ("📦 Inventory Items", "pages/inventory_items.py"),
        ("🗄️ Storage Locations", "pages/storage_locations.py"),
        ("🍽️ Kitchens", "pages/kitchens.py"),
    ]
    for label, target in core_items:
        st.sidebar.page_link(target, label=label)

    with st.sidebar.expander("More", expanded=False):
        st.page_link("pages/food_items.py", label="🥬 Food Items")
        st.page_link("pages/units.py", label="⚙️ Units")

    if is_superadmin:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Admin")
        st.sidebar.page_link("pages/users.py", label="👤 Users")
        st.sidebar.page_link("pages/user_credentials.py", label="🔐 User Credentials")
        st.sidebar.page_link("pages/user_health.py", label="🏥 User Health")

    st.sidebar.markdown("---")