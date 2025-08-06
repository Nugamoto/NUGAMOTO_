"""
NUGAMOTO Admin Frontend - Main Application Entry Point.

This script serves as the main entry point for the Streamlit application.
It sets up the global page configuration and displays the main landing page.
Streamlit automatically discovers and handles the navigation to other pages
located in the 'pages/' directory.
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    """
    Render the main landing page of the application.
    """
    st.set_page_config(
        page_title="NUGAMOTO Admin Dashboard",
        page_icon="🍳",  # Favicon
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": "https://www.nugamoto.com/help",
            "Report a bug": "https://www.nugamoto.com/bug",
            "About": "# NUGAMOTO - Smart Kitchen Assistant",
        },
    )

    st.title("Welcome to the NUGAMOTO Admin Dashboard 🍳")
    st.write(
        "Use the navigation sidebar on the left to manage different parts of "
        "the NUGAMOTO system."
    )

    st.divider()

    st.header("Available Management Pages:")

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.subheader("📦 Units")
            st.write("Manage measurement units like 'kg', 'liter', or 'piece'.")
            if st.button("Go to Units", key="nav_units"):
                st.switch_page("pages/units.py")

    with col2:
        with st.container(border=True):
            st.subheader("🍎 Food Items")
            st.write("Manage the master data for all food items.")
            if st.button("Go to Food Items", key="nav_food_items"):
                st.switch_page("pages/food_items.py")

    with col3:
        with st.container(border=True):
            st.subheader("🗄️ Storage Locations")
            st.write("Manage kitchen storage locations like 'fridge' or 'pantry'.")
            if st.button("Go to Storage Locations", key="nav_storage"):
                st.switch_page("pages/storage_locations.py")


if __name__ == "__main__":
    main()