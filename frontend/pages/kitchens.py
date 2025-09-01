"""Kitchens Management Page (pattern identical to Food-Items)."""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from clients import KitchensClient, APIException
except ImportError:
    from frontend.clients import KitchensClient, APIException


class KitchensController:
    """Same structure as FoodItemsController."""


    # ----------------------------- construction ---------------------- #
    def __init__(self) -> None:
        self.client = KitchensClient()
        # Tokens aus Session setzen (falls vorhanden)
        access = getattr(st.session_state, "auth_access_token", None)
        refresh = getattr(st.session_state, "auth_refresh_token", None)
        if access:
            self.client.set_tokens(access, refresh)
        self._init_state()

    @staticmethod
    def _init_state() -> None:
        st.session_state.setdefault("kitchens_rows", [])
        st.session_state.setdefault("show_add_kitchen", False)
        st.session_state.setdefault("show_edit_kitchen", False)
        st.session_state.setdefault("row_for_edit_kitchen", None)

    # ----------------------------- data ------------------------------ #
    def load_kitchens(self) -> list[dict[str, Any]]:
        try:
            rows = self.client.list_kitchens(limit=1000)
            st.session_state.kitchens_rows = sorted(rows, key=lambda x: x["id"])
            return st.session_state.kitchens_rows
        except APIException as exc:
            st.error(f"Load error: {exc.message}")
            return []

    # --------------------------- table -------------------------------- #
    @staticmethod
    def _render_table(rows: list[dict[str, Any]]) -> None:
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

        event = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            selection_mode="multi-row",
            on_select="rerun",
        )

        if event.selection.rows:
            sel = [rows[df.index[i]] for i in event.selection.rows]
            st.write(f"**{len(sel)} kitchen(s) selected**")
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

    # ------------------------ add / edit form ------------------------ #
    def _form(self, *, is_new: bool, defaults: dict[str, Any] | None = None) -> None:
        title = "Add Kitchen" if is_new else "Edit Kitchen"
        st.subheader(title)
        with st.form("kitchen_form", clear_on_submit=is_new):
            name = st.text_input("Kitchen Name*", value=defaults["name"] if defaults else "")
            col_s, col_c = st.columns(2)
            if col_s.form_submit_button("Save", type="primary"):
                if not name.strip():
                    st.error("Name required")
                else:
                    try:
                        if is_new:
                            self.client.create_kitchen({"name": name.strip()})
                        else:
                            self.client.update_kitchen(defaults["id"], {"name": name.strip()})
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

    # ------------------------------ render --------------------------- #
    def render(self) -> None:
        st.title("Kitchens")

        # Refresh / Add buttons
        col_r, col_a, _ = st.columns([1, 1, 6])
        if col_r.button("Refresh"):
            self.load_kitchens()
        if col_a.button("Add Kitchen"):
            st.session_state.show_add_kitchen = True

        st.divider()

        # Forms
        if st.session_state.show_add_kitchen:
            self._form(is_new=True)
            st.divider()
        if st.session_state.show_edit_kitchen and st.session_state.row_for_edit_kitchen:
            self._form(is_new=False, defaults=st.session_state.row_for_edit_kitchen)
            st.divider()

        # Table
        self._render_table(self.load_kitchens())


def main() -> None:
    st.set_page_config(page_title="Kitchens - NUGAMOTO")
    KitchensController().render()


if __name__ == "__main__":
    main()