"""Kitchens Management Page (pattern identical to Food-Items)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from frontend.utils.layout import render_sidebar
from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.clients import KitchensClient, APIException
from frontend.clients.inventory_items_client import InventoryItemsClient
from frontend.clients.storage_locations_client import StorageLocationsClient


class KitchensController:
    """Same structure as FoodItemsController."""


    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        render_sidebar()
        self.client = KitchensClient()
        self.inv_client = InventoryItemsClient()
        self.sl_client = StorageLocationsClient()
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.client.set_tokens(access, refresh)
            self.inv_client.set_tokens(access, refresh)
            self.sl_client.set_tokens(access, refresh)
        self._init_state()

    @staticmethod
    def _init_state() -> None:
        st.session_state.setdefault("kitchens_rows", [])
        st.session_state.setdefault("show_add_kitchen", False)
        st.session_state.setdefault("show_edit_kitchen", False)
        st.session_state.setdefault("row_for_edit_kitchen", None)
        st.session_state.setdefault("view_kitchen_id", None)
        st.session_state.setdefault("view_kitchen_name", None)
        st.session_state.setdefault("view_kitchen_role", None)
        st.session_state.setdefault("kitchen_active_tab", "Overview")
        st.session_state.setdefault("_last_topbar_kitchen_id", None)
        st.session_state.setdefault("_last_selected_row_kitchen_id", None)
        st.session_state.setdefault("_confirm_delete_kitchen", False)

    # ----------------------------- data ------------------------------ #
    def load_kitchens(self) -> list[dict[str, Any]]:
        try:
            rows = self.client.list_kitchens(limit=1000)
            st.session_state.kitchens_rows = sorted(rows, key=lambda x: x["id"])
            return st.session_state.kitchens_rows
        except APIException as exc:
            st.error(f"Load error: {exc.message}")
            return []


    # ----------------------------- helpers --------------------------- #
    @staticmethod
    def _resolve_role_for_current_user(details: dict[str, Any]) -> str | None:
        cu = st.session_state.get("current_user") or {}
        uid = cu.get("id")
        role = None
        for key in ("users", "user_kitchens", "members"):
            lst = details.get(key) or []
            for it in lst:
                if isinstance(it, dict):
                    if it.get("id") == uid and it.get("role"):
                        role = it.get("role")
                        break
                    if it.get("user_id") == uid and it.get("role"):
                        role = it.get("role")
                        break
                    if isinstance(it.get("user"), dict) and it["user"].get("id") == uid and it.get("role"):
                        role = it.get("role")
                        break
            if role:
                break
        return role


    def _open_kitchen(self, kitchen_id: int, name_hint: str | None = None) -> None:
        try:
            details = self.client.get_kitchen(kitchen_id)
            role = self._resolve_role_for_current_user(details)
            st.session_state.view_kitchen_id = kitchen_id
            st.session_state.view_kitchen_name = details.get("name") or name_hint or f"Kitchen {kitchen_id}"
            st.session_state.view_kitchen_role = role
            st.session_state.kitchen_active_tab = "Overview"
            st.session_state.selected_kitchen_id = kitchen_id
            st.session_state.selected_kitchen_name = st.session_state.view_kitchen_name
            st.session_state.selected_kitchen_role = role
            st.session_state._last_topbar_kitchen_id = kitchen_id
            st.rerun()
        except APIException as exc:
            st.error(f"Failed to open kitchen: {exc.message}")


    # --------------------------- table -------------------------------- #
    def _render_table(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            st.info("No kitchens stored yet.")
            return

        df = pd.DataFrame(
            {
                "ID": [r["id"] for r in rows],
                "Name": [r["name"] for r in rows],
                "Created": [r["created_at"][:10] for r in rows],
                "Updated": [r["updated_at"][:10] for r in rows],
            }
        ).sort_values("ID")

        st.caption("Tip: Click a row to open the kitchen details.")

        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun",
        )

        sel = []
        if event.selection.rows:
            sel = [rows[df.index[i]] for i in event.selection.rows]
            st.write(f"**{len(sel)} kitchen(s) selected**")

            if len(sel) == 1:
                current_id = int(sel[0]["id"])
                last_id = st.session_state.get("_last_selected_row_kitchen_id")
                if current_id != last_id:
                    st.session_state["_last_selected_row_kitchen_id"] = current_id
                    self._open_kitchen(current_id, name_hint=sel[0].get("name"))

            col_del, col_edit, _ = st.columns([1, 1, 6])
            if col_del.button("Delete Selected", type="secondary"):
                for r in sel:
                    try:
                        KitchensClient().delete_kitchen(r["id"])
                    except APIException as exc:
                        st.error(exc.message)
                st.rerun()

            if len(sel) == 1:
                if col_edit.button("Edit Selected"):
                    st.session_state.row_for_edit_kitchen = sel[0]
                    st.session_state.show_edit_kitchen = True
                    st.rerun()


    # ---------------------------- details ---------------------------- #
    def _render_detail_header(self, kitchen_id: int) -> None:
        name = st.session_state.get("view_kitchen_name") or f"Kitchen {kitchen_id}"
        role = st.session_state.get("view_kitchen_role")
        st.title(f"Kitchen · {name}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Kitchen", name)
        c2.metric("Kitchen ID", f"{kitchen_id}")
        c3.metric("Your Role", str(role).title() if role else "–")
        if st.button("Edit Kitchen", key="btn_hdr_edit_kitchen"):
            st.session_state.row_for_edit_kitchen = {"id": kitchen_id, "name": name}
            st.session_state.show_edit_kitchen = True
            st.rerun()
        if st.button("Delete Kitchen", key="btn_hdr_delete_kitchen", type="secondary"):
            st.session_state._confirm_delete_kitchen = True
            st.rerun()
        if st.session_state.get("_confirm_delete_kitchen"):
            st.warning("Delete this kitchen? This cannot be undone.")
            b1, b2 = st.columns(2)
            if b1.button("Confirm Delete", key="btn_hdr_conf_del", type="primary"):
                try:
                    self.client.delete_kitchen(kitchen_id)
                    st.session_state._confirm_delete_kitchen = False
                    st.session_state.view_kitchen_id = None
                    st.session_state.view_kitchen_name = None
                    st.session_state.view_kitchen_role = None
                    st.session_state.kitchen_active_tab = "Overview"
                    st.success("Kitchen deleted")
                    st.rerun()
                except APIException as exc:
                    st.error(exc.message)
            if b2.button("Cancel", key="btn_hdr_cancel_del"):
                st.session_state._confirm_delete_kitchen = False
                st.rerun()
        if st.button("← Back to Kitchens", key="btn_back_to_kitchens"):
            st.session_state.view_kitchen_id = None
            st.session_state.view_kitchen_name = None
            st.session_state.view_kitchen_role = None
            st.session_state.kitchen_active_tab = "Overview"
            st.rerun()


    def _render_detail_tabs(self, kitchen_id: int) -> None:
        tabs = st.tabs(["Overview", "Storage", "Inventory"])
        with tabs[0]:
            st.subheader("Overview")


            @st.cache_data(show_spinner=False, ttl=20)
            def _count_storage_locations(kid: int) -> int:
                try:
                    return len(self.sl_client.list_storage_locations(kid) or [])
                except APIException:
                    return 0


            @st.cache_data(show_spinner=False, ttl=20)
            def _count_inventory(kid: int) -> int:
                try:
                    return len(self.inv_client.list_inventory_items(kid) or [])
                except APIException:
                    return 0


            @st.cache_data(show_spinner=False, ttl=20)
            def _count_low_stock(kid: int) -> int:
                try:
                    return len(self.inv_client.get_low_stock_items(kid) or [])
                except APIException:
                    return 0


            @st.cache_data(show_spinner=False, ttl=20)
            def _count_expiring(kid: int, days: int = 7) -> int:
                try:
                    return len(self.inv_client.get_expiring_items(kid, threshold_days=days) or [])
                except APIException:
                    return 0


            a, b, c, d = st.columns(4)
            a.metric("Storage Locations", f"{_count_storage_locations(kitchen_id)}")
            b.metric("Inventory Items", f"{_count_inventory(kitchen_id)}")
            c.metric("Low Stock", f"{_count_low_stock(kitchen_id)}")
            d.metric("Expiring ≤7d", f"{_count_expiring(kitchen_id, 7)}")

            st.markdown("---")
            if st.button("Add Storage Location", key="btn_k_overview_add_storage"):
                st.warning("Not implemented yet.")
            if st.button("Add Inventory Item", key="btn_k_overview_add_item"):
                st.warning("Not implemented yet.")

        with tabs[1]:
            st.subheader("Storage")
            st.info("List of storage locations for this kitchen will appear here.")
            if st.button("Add Storage Location", key="btn_k_storage_add"):
                st.warning("Not implemented yet.")

        with tabs[2]:
            st.subheader("Inventory")
            st.info("Kitchen-wide inventory table with filters will appear here.")
            if st.button("Add Inventory Item", key="btn_k_inventory_add"):
                st.warning("Not implemented yet.")

    # ------------------------------ render --------------------------- #
    def render(self) -> None:
        st.title("Kitchens")

        selected_topbar_kid = st.session_state.get("selected_kitchen_id")
        last_topbar_kid = st.session_state.get("_last_topbar_kitchen_id")
        if selected_topbar_kid and selected_topbar_kid != last_topbar_kid:
            self._open_kitchen(int(selected_topbar_kid), name_hint=st.session_state.get("selected_kitchen_name"))
            return

        if st.session_state.get("view_kitchen_id"):
            kid = int(st.session_state.view_kitchen_id)
            self._render_detail_header(kid)
            self._render_detail_tabs(kid)
            return

        topbar_kid = st.session_state.get("selected_kitchen_id")
        topbar_name = st.session_state.get("selected_kitchen_name") or "Kitchen"
        if topbar_kid:
            if st.button(f"Open {topbar_name}", key="btn_open_from_topbar"):
                self._open_kitchen(int(topbar_kid), name_hint=topbar_name)

        if st.button("Add Kitchen", key="btn_add_kitchen"):
            st.session_state.show_add_kitchen = True

        st.divider()

        if st.session_state.show_add_kitchen:
            self._form(is_new=True)
            st.divider()
        if st.session_state.show_edit_kitchen and st.session_state.row_for_edit_kitchen:
            self._form(is_new=False, defaults=st.session_state.row_for_edit_kitchen)
            st.divider()

        self._render_table(self.load_kitchens())


def main() -> None:
    st.set_page_config(page_title="Kitchens - NUGAMOTO")
    KitchensController().render()


if __name__ == "__main__":
    main()