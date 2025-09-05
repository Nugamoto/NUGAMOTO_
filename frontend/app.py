from __future__ import annotations

import os
import sys

import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from frontend.clients.recipes_client import RecipesClient
from frontend.clients.inventory_items_client import InventoryItemsClient
from frontend.clients.kitchens_client import KitchensClient
from frontend.clients.base import APIException
from frontend.utils.sidebar import render_sidebar


def show_dashboard() -> None:
    render_sidebar()

    st.title("🏠 Dashboard")
    st.markdown("Welcome to your Smart Kitchen Assistant!")

    email = st.session_state.get("auth_email") or ""
    is_admin = bool(st.session_state.get("is_admin", False))
    if is_admin:
        st.success(f"🔑 Admin detected for {email}")
    else:
        st.info(f"Signed in as {email}")

    current_user = st.session_state.get("current_user") or {}
    user_id = current_user.get("id")
    if not user_id:
        st.warning("Login required.")
        st.switch_page("pages/login.py")

    kitchens_client = KitchensClient()
    recipes_client = RecipesClient()
    inventory_client = InventoryItemsClient()

    access = getattr(st.session_state, "auth_access_token", None)
    refresh = getattr(st.session_state, "auth_refresh_token", None)
    if access:
        for c in (kitchens_client, recipes_client, inventory_client):
            c.set_tokens(access, refresh)

    st.subheader("🍽️ Kitchen Context")

    @st.cache_data(show_spinner=False, ttl=30)
    def _load_member_kitchens_with_roles(_uid: int) -> list[dict]:
        rows = []
        try:
            all_kitchens = kitchens_client.list_kitchens(limit=1000) or []
        except APIException:
            all_kitchens = []
        for k in all_kitchens:
            kid = k.get("id")
            nm = k.get("name", f"Kitchen {kid}")
            if not kid:
                continue
            try:
                details = kitchens_client.get_kitchen(kid)
                role = None
                for key in ("users", "user_kitchens", "members"):
                    lst = details.get(key) or []
                    for it in lst:
                        if isinstance(it, dict):
                            if it.get("id") == _uid and it.get("role"):
                                role = it.get("role")
                                break
                            if it.get("user_id") == _uid and it.get("role"):
                                role = it.get("role")
                                break
                            if isinstance(it.get("user"), dict) and it["user"].get("id") == _uid and it.get("role"):
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


    kitchens = _load_member_kitchens_with_roles(int(user_id))
    if kitchens:
        labels = [f"{k['name']} ({k['role']})" for k in kitchens]
        idx = 0
        if st.session_state.get("selected_kitchen_id"):
            for i, k in enumerate(kitchens):
                if k["id"] == st.session_state["selected_kitchen_id"]:
                    idx = i
                    break
        sel = st.selectbox("Select your kitchen", options=range(len(labels)), index=idx,
                           format_func=lambda i: labels[i])
        chosen = kitchens[sel]
        st.session_state.selected_kitchen_id = chosen["id"]
        st.session_state.selected_kitchen_name = chosen["name"]
        st.session_state.selected_kitchen_role = chosen["role"]
        st.success(f"Active Kitchen: {chosen['name']} • Role: {str(chosen['role']).title()}")
        st.caption(f"Kitchen ID: {chosen['id']}")
    else:
        st.info("No kitchens available for your account yet.")

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
    st.set_page_config(page_title="Dashboard - NUGAMOTO")
    show_dashboard()


if __name__ == "__main__":
    main()