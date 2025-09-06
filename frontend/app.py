from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.clients.recipes_client import RecipesClient
from frontend.clients.inventory_items_client import InventoryItemsClient
from frontend.clients.base import APIException
from frontend.utils.layout import render_sidebar


def show_dashboard() -> None:
    render_sidebar()

    st.title("🏠 Dashboard")
    st.markdown("Welcome to your Smart Kitchen Assistant!")

    current_user = st.session_state.get("current_user") or {}
    user_id = current_user.get("id")
    if not user_id:
        st.warning("Login required.")
        st.switch_page("pages/login.py")

    recipes_client = RecipesClient()
    inventory_client = InventoryItemsClient()
    access = getattr(st.session_state, "auth_access_token", None)
    refresh = getattr(st.session_state, "auth_refresh_token", None)
    if access:
        for c in (recipes_client, inventory_client):
            c.set_tokens(access, refresh)

    @st.cache_data(show_spinner=False, ttl=15)
    def _count_my_recipes(_uid: int) -> int:
        try:
            rows = recipes_client.get_all_recipes(created_by_user_id=_uid, limit=1000)
            return len(rows or [])
        except APIException:
            return 0

    @st.cache_data(show_spinner=False, ttl=15)
    def _count_ai_recipes() -> int:
        try:
            rows = recipes_client.get_ai_generated_recipes(skip=0, limit=1000)
            return len(rows or [])
        except APIException:
            return 0

    @st.cache_data(show_spinner=False, ttl=15)
    def _count_inventory_items_for_kitchen(kid: int | None) -> int:
        if not kid:
            return 0
        try:
            rows = inventory_client.list_inventory_items(kid)
            return len(rows or [])
        except APIException:
            return 0

    my_recipes = _count_my_recipes(int(user_id))
    ai_recipes = _count_ai_recipes()
    inv_items = _count_inventory_items_for_kitchen(st.session_state.get("selected_kitchen_id"))

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("📖 My Recipes", f"{my_recipes}")
    with c2:
        st.metric("🤖 AI Recipes", f"{ai_recipes}")
    with c3:
        st.metric("📦 Inventory Items", f"{inv_items}")

    st.markdown("---")
    st.subheader("🚀 Quick Actions")
    a, b, c, d = st.columns(4)
    with a:
        if st.button("🤖 Generate AI Recipe", type="primary"):
            st.switch_page("pages/ai_recipes.py")
    with b:
        if st.button("📖 Browse Recipes"):
            st.switch_page("pages/recipes.py")
    with c:
        if st.button("📦 Manage Inventory"):
            st.switch_page("pages/inventory_items.py")
    with d:
        if st.button("🥬 Add Food Items"):
            st.switch_page("pages/food_items.py")

    st.markdown("---")
    st.subheader("📊 Recent Activity")
    st.info("In development.")


def main() -> None:
    st.set_page_config(page_title="Dashboard - NUGAMOTO", layout="wide")
    show_dashboard()


if __name__ == "__main__":
    main()