from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd
import streamlit as st

from frontend.utils.path import ensure_frontend_on_sys_path

ensure_frontend_on_sys_path(__file__)

from frontend.utils.layout import render_sidebar
from frontend.clients import (
    InventoryItemsClient,
    FoodItemsClient,
    StorageLocationsClient,
    APIException,
)


class InventoryController:
    """Encapsulates all UI and API logic for the inventory page."""

    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        render_sidebar()

        self.inv_client = InventoryItemsClient()
        self.food_client = FoodItemsClient()
        self.loc_client = StorageLocationsClient()

        # Tokens aus Session setzen (falls vorhanden)
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.inv_client.set_tokens(access, refresh)
            self.food_client.set_tokens(access, refresh)
            self.loc_client.set_tokens(access, refresh)

        self._init_state()

        # aktuell gewählte Kitchen lokal merken (für PATCH/DELETE)
        self.current_kitchen_id: int = int(st.session_state.get("kitchen_id", 1))

    @staticmethod
    def _init_state() -> None:
        defaults: dict[str, Any] = {
            "inv_rows": [],
            "food_master": [],
            "loc_master": [],
            "kitchen_id": 1,
            "show_add": False,
            "show_edit": False,
            "row_for_edit": None,
            "inv_filter": "All",
        }
        for key, val in defaults.items():
            st.session_state.setdefault(key, val)

    # ----------------------------- data loading ---------------------- #
    def _load_master_data(self, kitchen_id: int) -> None:
        """Load food items & storage locations into session-state."""
        self.current_kitchen_id = int(kitchen_id)
        try:
            st.session_state.food_master = self.food_client.list_food_items(limit=1000)
            st.session_state.loc_master = self.loc_client.list_storage_locations(
                kitchen_id
            )
        except APIException as exc:
            st.error(f"Failed to load master data: {exc.message}")

    def _load_inventory(self, kitchen_id: int) -> list[dict[str, Any]]:
        """Load inventory items and cache them."""
        try:
            rows = self.inv_client.list_inventory_items(kitchen_id)
            st.session_state.inv_rows = sorted(rows, key=lambda x: x["id"])
            return st.session_state.inv_rows
        except APIException as exc:
            st.error(f"Failed to load inventory: {exc.message}")
            return []

    # ----------------------------- helpers --------------------------- #
    @staticmethod
    def _unit_cell(item: dict[str, Any]) -> str:
        symbol = (
            item.get("food_item", {})
            .get("base_unit", {})
            .get("symbol")
        )
        return symbol or item.get("base_unit_name", "N/A")

    @staticmethod
    def _apply_filter(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return rows filtered according to current selection."""
        mode = st.session_state.get("inv_filter", "All")
        if mode == "Low stock":
            return [r for r in rows if r.get("is_low_stock")]
        if mode == "Expires soon":
            return [r for r in rows if r.get("expires_soon")]
        if mode == "Expired":
            return [r for r in rows if r.get("is_expired")]
        return rows

    # ------------------------- table rendering ----------------------- #
    def render_table(self, rows: list[dict[str, Any]]) -> None:
        """Render inventory rows and handle selection actions."""
        if not rows:
            st.info("No inventory items found for this kitchen.")
            return

        # Build DataFrame
        df = pd.DataFrame(
            {
                "ID": [r["id"] for r in rows],
                "Food": [r["food_item"]["name"] for r in rows],
                "Location": [r["storage_location"]["name"] for r in rows],
                "Quantity": [r["quantity"] for r in rows],
                "Min Quantity": [r.get("min_quantity") or "–" for r in rows],
                "Unit": [self._unit_cell(r) for r in rows],
                "Expires": [r.get("expiration_date") or "–" for r in rows],
                "Updated": [r["updated_at"][:10] for r in rows],
            }
        ).sort_values("ID")

        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun",
        )

        if event.selection.rows:
            selected = [rows[df.index[i]] for i in event.selection.rows]

            st.write(f"**{len(selected)} item(s) selected**")
            col_del, col_edit, _ = st.columns([1, 1, 4])

            if col_del.button("Delete Selected", type="secondary"):
                self._bulk_delete([r["id"] for r in selected])

            if len(selected) == 1:
                if col_edit.button("Edit Selected"):
                    st.session_state.row_for_edit = selected[0]
                    st.session_state.show_edit = True
                    st.rerun()

    # ----------------------------- CRUD helpers ---------------------- #
    def _bulk_delete(self, item_ids: list[int]) -> None:
        errors = 0
        for iid in item_ids:
            try:
                self.inv_client.delete_item(iid, kitchen_id=self.current_kitchen_id)
            except APIException:
                errors += 1
        if errors:
            st.error(f"Failed to delete {errors} item(s)")
        else:
            st.success("Item(s) deleted")
        st.rerun()

    def _save_item(
            self,
            *,
            is_new: bool,
            kitchen_id: int,
            payload: dict[str, Any],
            item_id: int | None = None,
    ) -> None:
        try:
            if is_new:
                self.inv_client.create_or_update_item(kitchen_id, payload)
            else:
                assert item_id is not None
                # PATCH erfordert kitchen_id als Query-Parameter
                self.inv_client.update_item_details(
                    item_id,
                    payload,
                    kitchen_id=kitchen_id,
                )
            st.success("Inventory item saved")
            st.session_state.show_add = False
            st.session_state.show_edit = False
            st.rerun()
        except APIException as exc:
            st.error(f"API error: {exc.message}")

    # ------------------------- add / edit form ----------------------- #
    def _render_form(
            self,
            *,
            is_new: bool,
            kitchen_id: int,
            defaults: dict[str, Any] | None = None,
    ) -> None:
        title = "Add Inventory Item" if is_new else "Edit Inventory Item"
        st.subheader(title)

        food_map = {
            f'{f["name"]} (ID {f["id"]})': f["id"]
            for f in st.session_state.food_master
        }
        loc_map = {
            f'{l["name"]} (ID {l["id"]})': l["id"]
            for l in st.session_state.loc_master
        }

        def _def(key: str) -> Any:
            return defaults.get(key) if defaults else None

        with st.form("inv_form", clear_on_submit=is_new):
            food_sel = st.selectbox(
                "Food Item",
                list(food_map.keys()),
                index=list(food_map.values()).index(_def("food_item_id"))
                if _def("food_item_id") in food_map.values()
                else 0,
            )
            loc_sel = st.selectbox(
                "Storage Location",
                list(loc_map.keys()),
                index=list(loc_map.values()).index(_def("storage_location_id"))
                if _def("storage_location_id") in loc_map.values()
                else 0,
            )

            qty = st.number_input(
                "Quantity (base unit)",
                min_value=0.0,
                step=0.1,
                value=float(_def("quantity") or 0),
            )
            min_qty = st.number_input(
                "Minimum Quantity (optional)",
                min_value=0.0,
                step=0.1,
                value=float(_def("min_quantity") or 0),
            )
            exp_date = st.date_input(
                "Expiration Date (optional)",
                value=dt.date.fromisoformat(_def("expiration_date"))
                if _def("expiration_date")
                else dt.date.today(),
            )

            col_save, col_cancel = st.columns(2)
            if col_save.form_submit_button("Save", type="primary"):
                payload: dict[str, Any] = {
                    "food_item_id": food_map[food_sel],
                    "storage_location_id": loc_map[loc_sel],
                    "quantity": qty,
                    "min_quantity": min_qty or None,
                    "expiration_date": exp_date.isoformat() if exp_date else None,
                }
                self._save_item(
                    is_new=is_new,
                    kitchen_id=kitchen_id,
                    payload=payload,
                    item_id=_def("id"),
                )

            if col_cancel.form_submit_button("Cancel"):
                st.session_state.show_add = False
                st.session_state.show_edit = False
                st.rerun()

    # ------------------------------ render --------------------------- #
    def render(self) -> None:
        """Main page renderer."""
        st.title("Inventory Items")

        # Kitchen selector
        kitchen_id = st.number_input(
            "Kitchen ID",
            min_value=1,
            step=1,
            key="kitchen_id",
        )
        self.current_kitchen_id = int(kitchen_id)
        self._load_master_data(self.current_kitchen_id)

        # Action buttons
        col_ref, col_add, _ = st.columns([1, 1, 6])
        if col_ref.button("Refresh"):
            self._load_inventory(self.current_kitchen_id)
        if col_add.button("Add Item"):
            st.session_state.show_add = True

        # Filter selector with Apply / Clear
        col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
        with col_f1:
            selected_mode = st.selectbox(
                "Filter",
                ("All", "Low stock", "Expires soon", "Expired"),
                index=(
                    "All",
                    "Low stock",
                    "Expires soon",
                    "Expired",
                ).index(st.session_state.inv_filter),
                key="inv_filter_select",
            )
        with col_f2:
            if st.button("Apply Filter"):
                st.session_state.inv_filter = selected_mode
                st.rerun()
        with col_f3:
            if st.button("Clear Filter"):
                st.session_state.inv_filter = "All"
                st.rerun()

        st.divider()

        # Forms
        if st.session_state.show_add:
            self._render_form(is_new=True, kitchen_id=self.current_kitchen_id)

        if st.session_state.show_edit and st.session_state.row_for_edit:
            self._render_form(
                is_new=False,
                kitchen_id=self.current_kitchen_id,
                defaults=st.session_state.row_for_edit,
            )

        # Data table
        all_rows = self._load_inventory(self.current_kitchen_id)
        filtered_rows = self._apply_filter(all_rows)
        self.render_table(filtered_rows)


def main() -> None:
    st.set_page_config(page_title="Inventory - NUGAMOTO")
    InventoryController().render()


if __name__ == "__main__":
    main()