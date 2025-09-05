from __future__ import annotations

import streamlit as st


def hide_native_pages_nav() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }
        .topbar-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 8px;
        }
        .topbar-title {
            font-weight: 700;
            font-size: 1.05rem;
            opacity: 0.9;
        }
        .topbar-right {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .pill {
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 0.85rem;
            border: 1px solid rgba(255,255,255,0.15);
            opacity: 0.95;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _perform_logout() -> None:
    st.session_state.auth_access_token = None
    st.session_state.auth_refresh_token = None
    st.session_state.auth_email = None
    st.session_state.is_admin = False
    st.session_state.current_user = None


def _render_topbar() -> None:
    hide_native_pages_nav()

    email = st.session_state.get("auth_email")
    is_admin = bool(st.session_state.get("is_admin", False))
    kitchen_name = st.session_state.get("selected_kitchen_name")
    kitchen_id = st.session_state.get("selected_kitchen_id")

    with st.container():
        st.markdown('<div class="topbar-container">', unsafe_allow_html=True)
        col_left, col_right = st.columns([3, 7])

        with col_left:
            st.markdown('<div class="topbar-title">NUGAMOTO</div>', unsafe_allow_html=True)

        with col_right:
            c1, c2, c3, c4 = st.columns([5, 2, 1, 2], vertical_alignment="center")
            with c1:
                if kitchen_name and kitchen_id:
                    st.markdown(
                        f'<div class="pill">🍳 {kitchen_name} · ID {kitchen_id}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<div class="pill">🍳 No kitchen selected</div>', unsafe_allow_html=True)
            with c2:
                if is_admin:
                    st.markdown('<div class="pill">Admin</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="pill">User</div>', unsafe_allow_html=True)
            with c3:
                st.button("Profile", key="tb_profile", on_click=lambda: st.switch_page("pages/profile.py"))
            with c4:
                if email:
                    if st.button("Logout", key="tb_logout"):
                        _perform_logout()
                        st.rerun()
                else:
                    st.button("Login", key="tb_login", on_click=lambda: st.switch_page("pages/login.py"))

        st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar() -> None:
    _render_topbar()

    st.sidebar.title("Navigation")

    nav_rows = [
        ("Dashboard", "app.py"),
        ("AI Recipes", "pages/ai_recipes.py"),
        ("Recipes", "pages/recipes.py"),
        ("Inventory Items", "pages/inventory_items.py"),
        ("Storage Locations", "pages/storage_locations.py"),
        ("Food Items", "pages/food_items.py"),
        ("Kitchens", "pages/kitchens.py"),
        ("Units", "pages/units.py"),
        ("Users", "pages/users.py"),
        ("User Credentials", "pages/user_credentials.py"),
        ("User Health", "pages/user_health.py"),
        ("Profile", "pages/profile.py"),
        ("Login", "pages/login.py"),
    ]

    col_a, col_b = st.sidebar.columns(2)
    half = (len(nav_rows) + 1) // 2
    for i, (label, target) in enumerate(nav_rows):
        col = col_a if i < half else col_b
        col.button(label, key=f"nav_{label.lower().replace(' ', '_')}", on_click=lambda t=target: st.switch_page(t))

    st.sidebar.markdown("---")

    email = st.session_state.get("auth_email") or "anonymous"
    is_admin = bool(st.session_state.get("is_admin", False))
    if is_admin:
        st.sidebar.success(f"Admin: {email}")
    else:
        st.sidebar.info(f"User: {email}")
