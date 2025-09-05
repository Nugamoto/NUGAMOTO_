from __future__ import annotations

import streamlit as st


def hide_native_pages_nav() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    hide_native_pages_nav()

    st.sidebar.title("NUGAMOTO")

    email = st.session_state.get("auth_email") or "User"
    is_admin = bool(st.session_state.get("is_admin", False))
    if is_admin:
        st.sidebar.success(f"Admin: {email}")
    else:
        st.sidebar.info(f"Welcome, {email}!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Kitchen Context")
    sel_name = st.session_state.get("selected_kitchen_name")
    sel_role = st.session_state.get("selected_kitchen_role")
    sel_id = st.session_state.get("selected_kitchen_id")
    if sel_id:
        role_label = str(sel_role).title() if isinstance(sel_role, str) else "Member"
        st.sidebar.button(
            f"🍳 Kitchen: {sel_name}",
            key="sb_kitchen_btn",
            help=f"ID {sel_id} · Role: {role_label}",
            use_container_width=True,
            disabled=True,
        )
    else:
        st.sidebar.caption("No kitchen selected")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")
    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        if st.button("Dashboard", key="nav_dashboard"):
            st.switch_page("app.py")
        if st.button("Inventory", key="nav_inventory"):
            st.switch_page("pages/inventory_items.py")
        if st.button("Food Items", key="nav_food"):
            st.switch_page("pages/food_items.py")
    with col_b:
        if st.button("Recipes", key="nav_recipes"):
            st.switch_page("pages/recipes.py")
        if st.button("Kitchens", key="nav_kitchens"):
            st.switch_page("pages/kitchens.py")
        if st.button("AI Recipes", key="nav_ai"):
            st.switch_page("pages/ai_recipes.py")
