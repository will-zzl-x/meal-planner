"""
Streamlit V1 entry point — login / register / logout, with an empty home
placeholder for now. Run with:

    streamlit run src/web/app.py

Database location is read from the MEAL_PLANNER_DB env var (default:
meal_planner.db in the current directory). The repository constructors
create the file and apply migrations the first time the app starts.

Session state:
- user: UserProfile when logged in; absent otherwise.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

# Make sibling packages importable when running via `streamlit run src/web/app.py`.
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.services.auth_service import (  # noqa: E402  (must come after sys.path tweak)
    AuthService,
    EmailAlreadyRegisteredError,
    HouseholdNotFoundError,
)
from repositories.sqlite.household_repository import SQLiteHouseholdRepository  # noqa: E402
from repositories.sqlite.user_repository import SQLiteUserRepository  # noqa: E402


DB_PATH = os.environ.get("MEAL_PLANNER_DB", "meal_planner.db")


@st.cache_resource
def get_auth_service() -> AuthService:
    """Build AuthService once per Streamlit process (cached across reruns)."""
    return AuthService(
        user_repo=SQLiteUserRepository(DB_PATH),
        household_repo=SQLiteHouseholdRepository(DB_PATH),
    )


def _missing_fields(fields: dict) -> list:
    """Return labels of any blank fields, for a single 'please fill in X, Y' error."""
    return [label for label, value in fields.items() if not value]


def render_login_form() -> None:
    st.subheader("Log in")
    with st.form("login"):
        email = st.text_input("Email").strip()
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log in")
    if not submit:
        return
    missing = _missing_fields({"Email": email, "Password": password})
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
        return
    user = get_auth_service().login(email, password)
    if user is None:
        st.error("Invalid email or password.")
        return
    st.session_state.user = user
    st.rerun()


def render_register_household_form() -> None:
    st.subheader("Start a new household")
    st.caption(
        "You'll become the planner for this household. "
        "Other people can join later using the household's invite code."
    )
    with st.form("register_household"):
        planner_name = st.text_input("Your name").strip()
        household_name = st.text_input("Household name").strip()
        email = st.text_input("Email").strip()
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Create household")
    if not submit:
        return
    missing = _missing_fields({
        "Name": planner_name,
        "Household name": household_name,
        "Email": email,
        "Password": password,
    })
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
        return
    try:
        result = get_auth_service().register_household(
            planner_name, email, password, household_name,
        )
    except EmailAlreadyRegisteredError:
        st.error("An account with that email already exists.")
        return
    st.session_state.user = result.user
    st.success(f"Household '{result.household.name}' created. Welcome, {result.user.name}!")
    st.rerun()


def render_register_member_form() -> None:
    st.subheader("Join an existing household")
    st.caption(
        "Ask the planner of your household for the invite code "
        "(they'll see it on their Household page)."
    )
    with st.form("register_member"):
        name = st.text_input("Your name").strip()
        email = st.text_input("Email").strip()
        password = st.text_input("Password", type="password")
        invite_code = st.text_input("Household invite code").strip()
        submit = st.form_submit_button("Join household")
    if not submit:
        return
    missing = _missing_fields({
        "Name": name, "Email": email, "Password": password, "Invite code": invite_code,
    })
    if missing:
        st.error(f"Please fill in: {', '.join(missing)}")
        return
    try:
        user = get_auth_service().register_member(name, email, password, invite_code)
    except HouseholdNotFoundError:
        st.error("That invite code doesn't match any household. Double-check it with the planner.")
        return
    except EmailAlreadyRegisteredError:
        st.error("An account with that email already exists.")
        return
    st.session_state.user = user
    st.success(f"Welcome to the household, {user.name}!")
    st.rerun()


def render_unauthenticated() -> None:
    st.title("Meal Planner")
    tab_login, tab_new, tab_join = st.tabs(["Log in", "Start a household", "Join a household"])
    with tab_login:
        render_login_form()
    with tab_new:
        render_register_household_form()
    with tab_join:
        render_register_member_form()


def render_authenticated() -> None:
    user = st.session_state.user
    with st.sidebar:
        st.write(f"**{user.name}**")
        st.caption("Planner" if user.is_planner else "Member")
        if st.button("Log out"):
            del st.session_state.user
            st.rerun()
    st.title(f"Welcome, {user.name}")
    st.info(
        "The rest of the app will live here in the next slice "
        "(recipes, pantry, weekly plan, today, etc.)."
    )


def main() -> None:
    st.set_page_config(page_title="Meal Planner", layout="centered")
    if "user" in st.session_state:
        render_authenticated()
    else:
        render_unauthenticated()


if __name__ == "__main__":
    main()
