from __future__ import annotations

import os

import streamlit as st

from frontend.clients.base import APIException
from frontend.clients.kitchens_client import KitchensClient


def hide_native_pages_nav() -> None:
    """Inject CSS to hide native nav and style the top bar."""
    st.markdown(
        """
        <style>
        /* Hide Streamlit's default sidebar page list */
        [data-testid="stSidebarNav"] { display: none !important; }
        section[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }

        /* Topbar container */
        .topbar {
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 16px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin: -1rem -1rem 0.25rem -1rem;
            box-sizing: border-box;
            flex-wrap: wrap;
            row-gap: 8px;
            column-gap: 12px;
        }

        /* Streamlit column wrappers inside topbar (left/right) */
        .topbar > div[data-testid="column"] {
            flex: 1 1 520px !important;
            min-width: 320px;
        }
        @media (max-width: 1200px) {
          .topbar > div[data-testid="column"] {
            flex: 1 1 100% !important;
            width: 100% !important;
          }
        }

        .label {
            opacity: 0.85;
            font-size: 0.9rem;
            white-space: nowrap;
        }

        /* Buttons kompakt */
        .stButton > button {
          white-space: nowrap;
          padding: 4px 10px;
          line-height: 1.1;
          font-size: 0.9rem;
        }
        .pill {
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 0.85rem;
            border: 1px solid rgba(255,255,255,0.15);
            opacity: 0.95;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 40vw;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _logo_path() -> str:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(project_root, "utils", "NUGAMOTO_logo.png")


def _perform_logout() -> None:
    st.session_state.auth_access_token = None
    st.session_state.auth_refresh_token = None
    st.session_state.auth_email = None
    st.session_state.is_admin = False
    st.session_state.current_user = None
    st.session_state._layout_needs_rerun = True


def _load_kitchens_for_user() -> list[dict]:
    user = st.session_state.get("current_user") or {}
    user_id = user.get("id")
    if not user_id:
        return []

    client = KitchensClient()
    access = st.session_state.get("auth_access_token")
    refresh = st.session_state.get("auth_refresh_token")
    if access:
        client.set_tokens(access, refresh)

    try:
        all_k = client.list_kitchens(limit=1000) or []
        rows: list[dict] = []
        for k in all_k:
            kid = k.get("id")
            nm = k.get("name", f"Kitchen {kid}")
            if not kid:
                continue
            try:
                details = client.get_kitchen(kid)
                role = None
                for key in ("users", "user_kitchens", "members"):
                    lst = details.get(key) or []
                    for it in lst:
                        if isinstance(it, dict):
                            if it.get("id") == user_id and it.get("role"):
                                role = it.get("role")
                                break
                            if it.get("user_id") == user_id and it.get("role"):
                                role = it.get("role")
                                break
                            if isinstance(it.get("user"), dict) and it["user"].get("id") == user_id and it.get("role"):
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
    except APIException:
        return []



def _render_topbar() -> None:
    """Render the top bar with compact kitchen selector and auth actions."""
    hide_native_pages_nav()

    email = st.session_state.get("auth_email")
    is_admin = bool(st.session_state.get("is_admin", False))

    with st.container():
        st.markdown('<div class="topbar">', unsafe_allow_html=True)

        # Rechts etwas breiter, damit Pill + Buttons nebeneinander passen
        left, right = st.columns([7, 5], vertical_alignment="center")

        # LEFT: Label + Select fest über Streamlit-Spalten (kein HTML-Wrapper)
        with left:
            if email:
                # c1 sehr schmal für das Label, c2 begrenzt die Select-Breite
                c1, c2 = st.columns([1, 3], vertical_alignment="center")
                with c1:
                    st.markdown('<span class="label">Kitchen:</span>', unsafe_allow_html=True)
                with c2:
                    kitchens = _load_kitchens_for_user()
                    if kitchens:
                        labels = [f"{k['name']} ({k['role']})" for k in kitchens]
                        default_idx = 0
                        if st.session_state.get("selected_kitchen_id"):
                            for i, k in enumerate(kitchens):
                                if k["id"] == st.session_state["selected_kitchen_id"]:
                                    default_idx = i
                                    break
                        sel = st.selectbox(
                            "Kitchen",
                            options=range(len(labels)),
                            index=default_idx,
                            format_func=lambda i: labels[i],
                            label_visibility="collapsed",
                            key="__topbar_kitchen_select__",
                        )
                        chosen = kitchens[sel]
                        st.session_state.selected_kitchen_id = chosen["id"]
                        st.session_state.selected_kitchen_name = chosen["name"]
                        st.session_state.selected_kitchen_role = chosen["role"]

        # RIGHT: Eine Zeile mit 3 Spalten – wie bei Quick Actions
        with right:
            r1, r2, r3 = st.columns([6, 2, 2], vertical_alignment="center")
            with r1:
                if email:
                    role_txt = "Admin" if is_admin else "User"
                    st.markdown(f'<span class="pill">👤 {email} · {role_txt}</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="pill">Not signed in</span>', unsafe_allow_html=True)
            with r2:
                st.button(
                    "Profile",
                    key="tb_profile_btn",
                    on_click=lambda: st.session_state.update(_nav_target="pages/profile.py"),
                    use_container_width=True,
                )
            with r3:
                if email:
                    if st.button("Logout", key="tb_logout_btn", use_container_width=True):
                        _perform_logout()
                else:
                    st.button(
                        "Login",
                        key="tb_login_btn",
                        on_click=lambda: st.session_state.update(_nav_target="pages/login.py"),
                        use_container_width=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.pop("_layout_needs_rerun", False):
        st.rerun()

    nav_target = st.session_state.pop("_nav_target", None)
    if nav_target:
        st.switch_page(nav_target)


def render_sidebar() -> None:
    """Render the left sidebar including navigation and dynamic 'More' section.

    Behavior:
        - Always shows Dashboard and core navigation items.
        - For admins, the 'More' expander lists all remaining *.py pages
          from the pages/ folder, excluding login/profile pages and
          anything already shown in core or admin sections.
        - For non-admins, 'More' keeps the original static entries.
    """
    _render_topbar()

    st.sidebar.image(
        _logo_path(),
        use_container_width=True,
        output_format="PNG",
        clamp=True,
        caption=None,
        channels="RGB",
    )
    st.sidebar.page_link("app.py", label="🏠 Dashboard", icon=None)
    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")

    current_user = st.session_state.get("current_user") or {}
    role = str(current_user.get("role", "") or "").lower()
    is_superadmin = bool(getattr(st.session_state, "is_superadmin", False)) or role == "superadmin"
    is_admin = bool(getattr(st.session_state, "is_admin", False))

    core_items: list[tuple[str, str]] = [
        ("🤖 AI Recipes", "pages/ai_recipes.py"),
        ("📖 Recipes", "pages/recipes.py"),
        ("📦 Inventory Items", "pages/inventory_items.py"),
        ("🗄️ Storage Locations", "pages/storage_locations.py"),
        ("🍽️ Kitchens", "pages/kitchens.py"),
    ]
    for label, target in core_items:
        st.sidebar.page_link(target, label=label)

    shown_targets: set[str] = {"app.py"} | {t for _, t in core_items}
    if is_superadmin:
        # Reserve admin pages to avoid duplicates in "More"
        shown_targets |= {
            "pages/users.py",
            "pages/user_credentials.py",
            "pages/user_health.py",
        }

    with st.sidebar.expander("More", expanded=False):
        if is_admin or is_superadmin:
            # Discover additional pages from the pages/ directory
            pages_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "pages")
            )
            try:
                file_names = [f for f in os.listdir(pages_dir) if f.endswith(".py")]
            except Exception:
                file_names = []

            # Exclude login and any profile-related pages and __init__.py
            excluded = {"login.py", "__init__.py"}
            file_names = [
                fname
                for fname in file_names
                if fname not in excluded and not fname.startswith("profile")
            ]

            # Build leftover list excluding already shown targets
            leftovers: list[tuple[str, str]] = []
            for fname in file_names:
                target = f"pages/{fname}"
                if target in shown_targets:
                    continue
                base = fname[:-3]  # strip .py
                # Derive a readable label from snake_case
                label = " ".join(part.capitalize() for part in base.split("_"))
                leftovers.append((label, target))

            leftovers.sort(key=lambda x: x[0].lower())

            if leftovers:
                for label, target in leftovers:
                    st.page_link(target, label=label)
            else:
                st.caption("No additional pages")
        else:
            # Non-admin fallback (original static entries)
            st.page_link("pages/food_items.py", label="🥬 Food Items")
            st.page_link("pages/units.py", label="⚙️ Units")

    if is_superadmin:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Admin")
        st.sidebar.page_link("pages/users.py", label="👤 Users")
        st.sidebar.page_link("pages/user_credentials.py", label="🔐 User Credentials")
        st.sidebar.page_link("pages/user_health.py", label="🏥 User Health")

    st.sidebar.markdown("---")
