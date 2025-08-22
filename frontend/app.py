"""Main Streamlit application for NUGAMOTO Smart Kitchen Assistant."""

import streamlit as st

# Configure page
st.set_page_config(
    page_title="NUGAMOTO Smart Kitchen",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """Main application entry point."""

    # Initialize session state
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None

    # Check authentication
    if not st.session_state.current_user:
        st.switch_page("pages/login.py")  # Ohne "frontend/" prefix
        return

    # Sidebar navigation
    with st.sidebar:
        st.title("🍳 NUGAMOTO")
        st.markdown(f"Welcome, **{st.session_state.current_user.get('name', 'User')}**!")

        # Kitchen selection (if available)
        if hasattr(st.session_state, 'selected_kitchen_id'):
            st.info(f"📍 Kitchen: {st.session_state.get('selected_kitchen_name', 'Unknown')}")

        st.markdown("---")

        # Navigation menu
        page = st.selectbox(
            "Navigation",
            [
                "🏠 Dashboard",
                "📖 Recipes",
                "🤖 AI Recipes",
                "📦 Inventory",
                "🥬 Food Items",
                "🏪 Storage Locations",
                "⚖️ Units",
                "🏠 Kitchens",
                "👥 Users",
                "🔐 Credentials",
                "💊 Health",
            ]
        )

        st.markdown("---")

        # Logout button
        if st.button("🚪 Logout"):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Route to appropriate page
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "📖 Recipes":
        st.switch_page("pages/recipes.py")  # Ohne "frontend/" prefix
    elif page == "🤖 AI Recipes":
        st.switch_page("pages/ai_recipes.py")  # Ohne "frontend/" prefix
    elif page == "📦 Inventory":
        st.switch_page("pages/inventory_items.py")
    elif page == "🥬 Food Items":
        st.switch_page("pages/food_items.py")
    elif page == "🏪 Storage Locations":
        st.switch_page("pages/storage_locations.py")
    elif page == "⚖️ Units":
        st.switch_page("pages/units.py")
    elif page == "🏠 Kitchens":
        st.switch_page("pages/kitchens.py")
    elif page == "👥 Users":
        st.switch_page("pages/users.py")
    elif page == "🔐 Credentials":
        st.switch_page("pages/user_credentials.py")
    elif page == "💊 Health":
        st.switch_page("pages/user_health.py")


def show_dashboard():
    """Display main dashboard."""
    st.title("🏠 Dashboard")
    st.markdown("Welcome to your Smart Kitchen Assistant!")

    # Quick stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📖 My Recipes", "0", help="Number of your saved recipes")

    with col2:
        st.metric("🤖 AI Recipes", "0", help="Number of AI-generated recipes")

    with col3:
        st.metric("📦 Inventory Items", "0", help="Number of items in your kitchen inventory")

    st.markdown("---")

    # Quick actions
    st.subheader("🚀 Quick Actions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🤖 Generate AI Recipe", type="primary"):
            st.switch_page("pages/ai_recipes.py")

    with col2:
        if st.button("📖 Browse Recipes"):
            st.switch_page("pages/recipes.py")

    with col3:
        if st.button("📦 Manage Inventory"):
            st.switch_page("pages/inventory_items.py")

    with col4:
        if st.button("🥬 Add Food Items"):
            st.switch_page("pages/food_items.py")

    # Recent activity section
    st.markdown("---")
    st.subheader("📊 Recent Activity")
    st.info("Your recent activities will be displayed here (in development).")


if __name__ == "__main__":
    main()