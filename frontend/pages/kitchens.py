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
    """Kitchens page controller with Kitchen list and detail view (Overview, Storage, Inventory)."""

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
        # List (landing) state
        st.session_state.setdefault("kitchens_rows", [])
        st.session_state.setdefault("show_add_kitchen", False)
        st.session_state.setdefault("show_edit_kitchen", False)
        st.session_state.setdefault("row_for_edit_kitchen", None)

        # Detail state
        st.session_state.setdefault("view_kitchen_id", None)
        st.session_state.setdefault("view_kitchen_name", None)
        st.session_state.setdefault("view_kitchen_role", None)
        st.session_state.setdefault("kitchen_active_tab", "Overview")

        # Misc
        st.session_state.setdefault("_last_topbar_kitchen_id", None)
        st.session_state.setdefault("_last_selected_row_kitchen_id", None)
        st.session_state.setdefault("_confirm_delete_kitchen", False)

        # (kept for compatibility; no actions in watch-only tabs)
        st.session_state.setdefault("storage_show_add", False)

    def load_kitchens(self) -> list[dict[str, Any]]:
        """Load kitchens the current user belongs to. Return [] on 403 to trigger empty-state."""
        try:
            rows = self.client.list_kitchens(limit=1000)
            st.session_state.kitchens_rows = sorted(rows, key=lambda x: x["id"])
            return st.session_state.kitchens_rows
        except APIException as exc:
            if getattr(exc, "status_code", None) == 403:
                # No memberships yet (typical for new users)
                st.session_state.kitchens_rows = []
                return []
            st.error(f"Load error: {exc.message}")
            return []


    def _empty_state_for_new_users(self) -> None:
        """Show friendly onboarding when user has no kitchen memberships."""
        st.info("It looks like you are not a member of any kitchen yet.")
        col_left, col_right = st.columns([1, 1])

        # Create kitchen (become Owner)
        with col_left:
            st.subheader("Create your own kitchen")
            st.caption("You'll become the Owner and can invite others.")
            if st.button("➕ Create Kitchen", key="btn_create_first_kitchen"):
                st.session_state.show_add_kitchen = True
                st.experimental_rerun()

        # Request access to an existing kitchen (manual contact for now)
        with col_right:
            st.subheader("Join an existing kitchen")
            st.caption(
                "Ask the kitchen owner to add your account email to the members. "
                "Once added, the kitchen will appear here."
            )
            with st.expander("I know the Kitchen ID (optional)", expanded=False):
                _ = st.text_input("Kitchen ID (ask the owner)", value="", key="join_req_kid")
                _ = st.text_input("Owner email (optional)", value="", key="join_req_owner")
                if st.button("I have contacted the owner", key="btn_mark_contacted"):
                    st.success(
                        "Great! The owner can add you on the Kitchens page. "
                        "You'll see the kitchen here once added."
                    )


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

    @staticmethod
    def _is_owner_or_admin(role: str | None) -> bool:
        return str(role or "").lower() in {"owner", "admin"}

    @staticmethod
    def _is_member_or_higher(role: str | None) -> bool:
        return str(role or "").lower() in {"member", "owner", "admin"}

    def _open_kitchen(self, kitchen_id: int, name_hint: str | None = None) -> None:
        """Load details for a kitchen and enter the detail view."""
        try:
            details = self.client.get_kitchen(kitchen_id)
            role = self._resolve_role_for_current_user(details)

            st.session_state.view_kitchen_id = kitchen_id
            st.session_state.view_kitchen_name = details.get("name") or name_hint or f"Kitchen {kitchen_id}"
            st.session_state.view_kitchen_role = role
            st.session_state.kitchen_active_tab = "Overview"

            # Sync topbar
            st.session_state.selected_kitchen_id = kitchen_id
            st.session_state.selected_kitchen_name = st.session_state.view_kitchen_name
            st.session_state.selected_kitchen_role = role
            st.session_state._last_topbar_kitchen_id = kitchen_id

            st.rerun()
        except APIException as exc:
            if getattr(exc, "status_code", None) == 403:
                st.warning(
                    "You don't have access to this kitchen. "
                    "Please select a kitchen you belong to or create your own."
                )
            else:
                st.error(f"Failed to open kitchen: {exc.message}")

    def _form(self, *, is_new: bool, defaults: dict[str, Any] | None = None) -> None:
        """Add/Edit Kitchen form (used on landing and in header inline)."""
        title = "Add Kitchen" if is_new else "Edit Kitchen"
        st.subheader(title)
        with st.form("kitchen_form", clear_on_submit=is_new):
            name = st.text_input("Kitchen Name*", value=(defaults or {}).get("name", ""))
            col_s, col_c = st.columns(2)
            if col_s.form_submit_button("Save", type="primary"):
                if not name.strip():
                    st.error("Name required")
                else:
                    try:
                        if is_new:
                            self.client.create_kitchen({"name": name.strip()})
                        else:
                            assert defaults is not None
                            self.client.update_kitchen(int(defaults["id"]), {"name": name.strip()})
                        st.success("Saved")
                        st.session_state.show_add_kitchen = False
                        st.session_state.show_edit_kitchen = False
                        st.rerun()
                    except APIException as exc:
                        st.error(exc.message)
            if col_c.form_submit_button("Cancel"):
                st.session_state.show_add_kitchen = False
                st.session_state.show_edit_kitchen = False
                st.rerun()

    def _render_table(self, rows: list[dict[str, Any]]) -> None:
        """Landing table with selection and action buttons."""
        if not rows:
            self._empty_state_for_new_users()
            return

        df = pd.DataFrame(
            {
                "ID": [r["id"] for r in rows],
                "Name": [r["name"] for r in rows],
                "Created": [r.get("created_at", "")[:10] for r in rows],
                "Updated": [r.get("updated_at", "")[:10] for r in rows],
            }
        ).sort_values("ID")

        st.caption("Select rows to enable actions below.")
        event = st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun",
        )

        sel: list[dict[str, Any]] = []
        if event.selection.rows:
            sel = [rows[df.index[i]] for i in event.selection.rows]
            st.write(f"**{len(sel)} kitchen(s) selected**")

        if len(sel) > 0:
            if st.button("Delete Selected", key="btn_delete_selected", type="secondary"):
                for r in sel:
                    try:
                        KitchensClient().delete_kitchen(int(r["id"]))
                    except APIException as exc:
                        st.error(exc.message)
                st.rerun()

        if len(sel) == 1:
            if st.button("Edit Selected", key="btn_edit_selected"):
                st.session_state.row_for_edit_kitchen = sel[0]
                st.session_state.show_edit_kitchen = True
                st.rerun()

    def _render_detail_header(self, kitchen_id: int) -> None:
        """Header for detail view with inline Edit/Delete and back button."""
        name = st.session_state.get("view_kitchen_name") or f"Kitchen {kitchen_id}"
        role = st.session_state.get("view_kitchen_role")

        st.title(f"Kitchen · {name}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Kitchen", name)
        c2.metric("Kitchen ID", f"{kitchen_id}")
        c3.metric("Your Role", str(role).title() if role else "–")

        if st.button("Edit Kitchen", key="btn_hdr_edit_kitchen"):
            st.session_state.show_edit_kitchen = True
            st.session_state.row_for_edit_kitchen = {"id": kitchen_id, "name": name}
            st.rerun()

        if self._is_owner_or_admin(role):
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
                    st.success("Kitchen deleted")
                    st.rerun()
                except APIException as exc:
                    st.error(exc.message)
            if b2.button("Cancel", key="btn_hdr_cancel_del"):
                st.session_state._confirm_delete_kitchen = False
                st.rerun()

        if st.session_state.get("show_edit_kitchen") and st.session_state.get("row_for_edit_kitchen"):
            self._form(is_new=False, defaults=st.session_state.row_for_edit_kitchen)
            st.divider()

        if st.button("← Back to Kitchens", key="btn_back_to_kitchens"):
            st.session_state.view_kitchen_id = None
            st.session_state.view_kitchen_name = None
            st.session_state.view_kitchen_role = None
            st.session_state.kitchen_active_tab = "Overview"
            st.rerun()

    def _render_detail_tabs(self, kitchen_id: int) -> None:
        """Detail view tabs: Overview (metrics), Storage (watch-only expanders), Inventory (filter + table)."""
        tabs = st.tabs(["Overview", "Storage", "Inventory"])

        # Overview
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

        # Storage (watch-only expanders)
        with tabs[1]:
            st.subheader("Storage")

            def _load_storage() -> list[dict[str, Any]]:
                try:
                    return self.sl_client.list_storage_locations(kitchen_id) or []
                except APIException as exc:
                    st.error(f"Failed to load storage locations: {exc.message}")
                    return []

            def _load_inventory() -> list[dict[str, Any]]:
                try:
                    return self.inv_client.list_inventory_items(kitchen_id) or []
                except APIException:
                    return []

            if st.button("Manage Storage Locations", key="btn_go_manage_storage"):
                st.switch_page("pages/storage_locations.py")

            st.divider()

            storage_rows = _load_storage()
            inv_rows = _load_inventory()

            if not storage_rows:
                st.info("No storage locations yet.")
            else:
                for loc in storage_rows:
                    lid = int(loc["id"])
                    lname = loc.get("name", f"Location {lid}")
                    with st.expander(f"🗄️ {lname} · ID {lid}", expanded=False):
                        loc_items = [it for it in inv_rows if int(it.get("storage_location_id") or 0) == lid]
                        if not loc_items:
                            st.info("No items in this location.")
                        else:
                            df_items = pd.DataFrame(
                                {
                                    "Food": [
                                        (it.get("food_item") or {}).get("name", f"Food {it.get('food_item_id')}")
                                        for it in loc_items
                                    ],
                                    "Quantity": [it.get("quantity") for it in loc_items],
                                    "Unit": [
                                        ((it.get("food_item") or {}).get("base_unit") or {}).get("name", "")
                                        for it in loc_items
                                    ],
                                    "Min": [it.get("min_quantity") for it in loc_items],
                                    "Expiration": [it.get("expiration_date") or "–" for it in loc_items],
                                    "Status": [
                                        "LOW" if (it.get("min_quantity") is not None and it.get("quantity") is not None
                                                  and it["quantity"] < it["min_quantity"]) else ""
                                        for it in loc_items
                                    ],
                                }
                            )
                            st.dataframe(df_items, width="stretch", hide_index=True)

        # Inventory (filter + table)
        with tabs[2]:
            st.subheader("Inventory")

            def _load_storage_i() -> list[dict[str, Any]]:
                try:
                    return self.sl_client.list_storage_locations(kitchen_id) or []
                except APIException:
                    return []

            def _load_inventory_i() -> list[dict[str, Any]]:
                try:
                    return self.inv_client.list_inventory_items(kitchen_id) or []
                except APIException:
                    return []

            locs = _load_storage_i()
            options = [("all", "All Locations")] + [(str(l["id"]), l.get("name", f"Location {l['id']}")) for l in locs]
            idx = st.selectbox(
                "Filter by Location",
                options=range(len(options)),
                format_func=lambda i: options[i][1],
                key="inv_filter_location",
            )
            sel_loc = options[idx][0]

            st.divider()

            items = _load_inventory_i()
            filtered = items if sel_loc == "all" else [i for i in items if str(i.get("storage_location_id")) == sel_loc]

            if not filtered:
                st.info("No inventory items.")
            else:
                def _loc_name(lid: int) -> str:
                    for l in locs:
                        if int(l["id"]) == lid:
                            return l.get("name", f"Location {lid}")
                    return f"Location {lid}"

                def _status(it: dict) -> str:
                    q = it.get("quantity")
                    mn = it.get("min_quantity")
                    exp = it.get("expiration_date")
                    s = []
                    if mn is not None and q is not None and q < mn:
                        s.append("LOW")
                    if exp:
                        s.append("EXP")
                    return ", ".join(s)

                df_inv = pd.DataFrame(
                    {
                        "Food": [
                            (it.get("food_item") or {}).get("name", f"Food {it.get('food_item_id')}")
                            for it in filtered
                        ],
                        "Location": [_loc_name(int(it.get("storage_location_id") or 0)) for it in filtered],
                        "Quantity": [it.get("quantity") for it in filtered],
                        "Unit": [
                            ((it.get("food_item") or {}).get("base_unit") or {}).get("name", "")
                            for it in filtered
                        ],
                        "Min": [it.get("min_quantity") for it in filtered],
                        "Expiration": [it.get("expiration_date") or "–" for it in filtered],
                        "Status": [_status(it) for it in filtered],
                    }
                ).sort_values(["Location", "Food"])
                st.dataframe(df_inv, width="stretch", hide_index=True)

    def render(self) -> None:
        """Top-level router: list vs detail, with new-user onboarding."""
        st.title("Kitchens")

        # Sync from topbar to detail
        selected_topbar_kid = st.session_state.get("selected_kitchen_id")
        last_topbar_kid = st.session_state.get("_last_topbar_kitchen_id")
        if selected_topbar_kid and selected_topbar_kid != last_topbar_kid:
            self._open_kitchen(int(selected_topbar_kid), name_hint=st.session_state.get("selected_kitchen_name"))
            return

        # Detail mode
        if st.session_state.get("view_kitchen_id"):
            kid = int(st.session_state.view_kitchen_id)
            self._render_detail_header(kid)
            self._render_detail_tabs(kid)
            return

        # Landing (list) with primary CTAs
        topbar_kid = st.session_state.get("selected_kitchen_id")
        topbar_name = st.session_state.get("selected_kitchen_name") or "Kitchen"
        if topbar_kid:
            if st.button(f"Open {topbar_name}", key="btn_open_from_topbar"):
                self._open_kitchen(int(topbar_kid), name_hint=topbar_name)

        c_add, c_refresh, _ = st.columns([1, 1, 6])
        if c_add.button("➕ Add Kitchen", key="btn_add_kitchen"):
            st.session_state.show_add_kitchen = True
        if c_refresh.button("🔄 Refresh", key="btn_refresh_kitchens"):
            self.load_kitchens()

        st.divider()

        if st.session_state.show_add_kitchen:
            self._form(is_new=True)
            st.divider()
        if st.session_state.show_edit_kitchen and st.session_state.row_for_edit_kitchen and not st.session_state.get(
                "view_kitchen_id"):
            self._form(is_new=False, defaults=st.session_state.row_for_edit_kitchen)
            st.divider()

        self._render_table(self.load_kitchens())


def main() -> None:
    st.set_page_config(page_title="Kitchens - NUGAMOTO")
    KitchensController().render()


if __name__ == "__main__":
    main()
