"""NUGAMOTO Admin Frontend - Main Application."""

import streamlit as st


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="NUGAMOTO Admin",
        page_icon="🍳",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🍳 NUGAMOTO Admin")
    st.write("Welcome to NUGAMOTO Smart Kitchen Assistant Admin Panel")

    # Basic functionality test
    name = st.text_input("Enter your name:")
    if name:
        st.success(f"Hello {name}! 👋")

    if st.button("Test Connection"):
        st.info("Ready to connect to API!")


if __name__ == "__main__":
    main()