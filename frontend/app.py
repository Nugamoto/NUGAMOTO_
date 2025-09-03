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
        st.switch_page("pages/login.py")

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

    # Admin-Badge (Token-basiert)
    is_admin = bool(getattr(st.session_state, "is_admin", False))
    current_user = st.session_state.get("current_user") or {}
    user_email = current_user.get("email", "")
    with st.container(border=True):
        if is_admin:
            st.success(f"🔑 Admin detected for {user_email}")
        else:
            st.info(f"🔒 Standard user: {user_email}")


    # ---------------------------------------------------------------
    # Kitchen selection with role (persisted in session_state)
    # ---------------------------------------------------------------
    current_user = st.session_state.get("current_user") or {}
    user_id = current_user.get("id")

    if not user_id:
        st.warning("User context missing. Please login again.")
        st.switch_page("pages/login.py")

    # Lazy import clients and attach tokens
    try:
        from frontend.clients.kitchens_client import KitchensClient
        from frontend.clients.recipes_client import RecipesClient
        from frontend.clients.inventory_items_client import InventoryItemsClient
        from frontend.clients.base import APIException
    except Exception:
        from clients.kitchens_client import KitchensClient
        from clients.recipes_client import RecipesClient
        from clients.inventory_items_client import InventoryItemsClient
        from clients.base import APIException

    access = getattr(st.session_state, "auth_access_token", None)
    refresh = getattr(st.session_state, "auth_refresh_token", None)

    kitchens_client = KitchensClient()
    recipes_client = RecipesClient()
    inventory_client = InventoryItemsClient()

    if access:
        kitchens_client.set_tokens(access, refresh)
        recipes_client.set_tokens(access, refresh)
        inventory_client.set_tokens(access, refresh)


    def _extract_user_role_from_kitchen_payload(payload: dict, uid: int) -> str | None:
        candidates = []
        for key in ("users", "user_kitchens", "members"):
            val = payload.get(key)
            if isinstance(val, list):
                candidates = val
                break
        for item in candidates:
            if not isinstance(item, dict):
                continue
            if item.get("id") == uid and item.get("role"):
                return str(item["role"])
            if item.get("user_id") == uid and item.get("role"):
                return str(item["role"])
            if isinstance(item.get("user"), dict) and item["user"].get("id") == uid:
                if item.get("role"):
                    return str(item["role"])
        return None


    @st.cache_data(show_spinner=False, ttl=30)
    def _load_member_kitchens_with_roles(_uid: int) -> list[dict]:
        try:
            all_kitchens = kitchens_client.list_kitchens(limit=1000) or []
        except APIException:
            all_kitchens = []
        member_kitchens: list[dict] = []
        for k in all_kitchens:
            kid = k.get("id")
            name = k.get("name", f"Kitchen {kid}")
            if not kid:
                continue
            try:
                details = kitchens_client.get_kitchen(kid)
                role = _extract_user_role_from_kitchen_payload(details, _uid)
                if role:
                    member_kitchens.append({"id": kid, "name": name, "role": role})
            except APIException:
                continue
        member_kitchens.sort(key=lambda r: str(r.get("name", "")).lower())
        return member_kitchens


    user_kitchens = _load_member_kitchens_with_roles(int(user_id))

    with st.container(border=True):
        st.subheader("🍽️ Kitchen Context")
        if not user_kitchens:
            st.info("No kitchens available for your account yet.")
        else:
            options = [f"{k['name']} ({k['role']})" for k in user_kitchens]
            option_index = 0
            current_selected_id = st.session_state.get("selected_kitchen_id")
            if current_selected_id:
                for idx, k in enumerate(user_kitchens):
                    if k["id"] == current_selected_id:
                        option_index = idx
                        break
            sel = st.selectbox(
                "Select your kitchen",
                options=range(len(options)),
                index=option_index,
                format_func=lambda i: options[i],
                key="__dashboard_kitchen_select__",
            )
            chosen = user_kitchens[sel]
            st.session_state.selected_kitchen_id = chosen["id"]
            st.session_state.selected_kitchen_name = chosen["name"]
            st.session_state.selected_kitchen_role = chosen["role"]

            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.success(
                    f"Active Kitchen: {chosen['name']}  •  Role: {chosen['role'].title()}"
                )
            with col_b:
                st.caption(f"Kitchen ID: {chosen['id']}")


    # ---------------------------------------------------------------
    # Live metrics (Recipes, AI Recipes, Inventory Items)
    # ---------------------------------------------------------------
    @st.cache_data(show_spinner=False, ttl=15)
    def _count_my_recipes(_uid: int) -> int:
        try:
            rows = recipes_client.get_all_recipes(created_by_user_id=_uid, limit=1_000)
            return len(rows or [])
        except APIException:
            return 0
        except Exception:
            return 0


    @st.cache_data(show_spinner=False, ttl=15)
    def _count_ai_recipes() -> int:
        try:
            rows = recipes_client.get_ai_generated_recipes(skip=0, limit=1_000)
            return len(rows or [])
        except APIException:
            return 0
        except Exception:
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
        except Exception:
            return 0


    my_recipes_count = _count_my_recipes(int(user_id))
    ai_recipes_count = _count_ai_recipes()
    inv_items_count = _count_inventory_items_for_kitchen(st.session_state.get("selected_kitchen_id"))

    st.markdown("---")

    # Quick stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📖 My Recipes", f"{my_recipes_count}", help="Number of your saved recipes")
    with col2:
        st.metric("🤖 AI Recipes", f"{ai_recipes_count}", help="Number of AI-generated recipes")
    with col3:
        st.metric(
            "📦 Inventory Items",
            f"{inv_items_count}",
            help="Number of items in your selected kitchen inventory",
        )

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