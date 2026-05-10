"""
Streamlit V1 entry point. Run with:

    streamlit run src/web/app.py

Database location is read from the MEAL_PLANNER_DB env var (default:
meal_planner.db). The repository constructors create the file and apply
migrations the first time the app starts.

Routing:
- Logged out → tabbed auth screen (login / start household / join household).
- Logged in  → multipage app via st.navigation, with sidebar log-out.

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

from core.services.auth_service import (  # noqa: E402
    AuthService,
    EmailAlreadyRegisteredError,
    HouseholdNotFoundError,
)
from core.services.flexible_dieting import BodyCompositionService  # noqa: E402
from core.services.food_database_service import FoodDatabaseService  # noqa: E402
from core.services.grocery_list_service import GroceryListService  # noqa: E402
from core.services.recipe_calorie_calculator import RecipeCalorieCalculator  # noqa: E402
from repositories.sqlite.food_log_repository import SQLiteFoodLogRepository  # noqa: E402
from repositories.sqlite.household_repository import SQLiteHouseholdRepository  # noqa: E402
from repositories.sqlite.ingredient_catalog_repository import (  # noqa: E402
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository  # noqa: E402
from repositories.sqlite.meal_plan_repository import SQLiteMealPlanRepository  # noqa: E402
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository  # noqa: E402
from repositories.sqlite.user_repository import SQLiteUserRepository  # noqa: E402


DB_PATH = os.environ.get("MEAL_PLANNER_DB", "meal_planner.db")


# --- Cached singletons ----------------------------------------------------

@st.cache_resource
def get_auth_service() -> AuthService:
    return AuthService(
        user_repo=SQLiteUserRepository(DB_PATH),
        household_repo=SQLiteHouseholdRepository(DB_PATH),
        recipe_repo=SQLiteRecipeRepository(DB_PATH),  # auto-seeds new households
    )


@st.cache_resource
def get_recipe_repo() -> SQLiteRecipeRepository:
    return SQLiteRecipeRepository(DB_PATH)


@st.cache_resource
def get_inventory_repo() -> SQLiteInventoryRepository:
    return SQLiteInventoryRepository(DB_PATH)


@st.cache_resource
def get_household_repo() -> SQLiteHouseholdRepository:
    return SQLiteHouseholdRepository(DB_PATH)


@st.cache_resource
def get_meal_plan_repo() -> SQLiteMealPlanRepository:
    return SQLiteMealPlanRepository(DB_PATH)


@st.cache_resource
def get_grocery_service() -> GroceryListService:
    return GroceryListService()


@st.cache_resource
def get_food_log_repo() -> SQLiteFoodLogRepository:
    return SQLiteFoodLogRepository(DB_PATH)


@st.cache_resource
def get_user_repo() -> SQLiteUserRepository:
    return SQLiteUserRepository(DB_PATH)


@st.cache_resource
def get_body_composition_service() -> BodyCompositionService:
    return BodyCompositionService()


@st.cache_resource
def get_food_database() -> FoodDatabaseService:
    return FoodDatabaseService()


@st.cache_resource
def get_catalog_repo() -> SQLiteIngredientCatalogRepository:
    return SQLiteIngredientCatalogRepository(DB_PATH)


@st.cache_resource
def get_calorie_calculator() -> RecipeCalorieCalculator:
    return RecipeCalorieCalculator(get_catalog_repo())


# --- Auth screens ---------------------------------------------------------

def _missing_fields(fields: dict) -> list:
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
        "Name": planner_name, "Household name": household_name,
        "Email": email, "Password": password,
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


# --- Authenticated shell --------------------------------------------------

def _render_sidebar() -> None:
    user = st.session_state.user
    with st.sidebar:
        st.write(f"**{user.name}**")
        st.caption("Planner" if user.is_planner else "Member")
        if st.button("Log out"):
            del st.session_state.user
            st.rerun()


def recipes_page_entry() -> None:
    from web.views import recipes
    _render_sidebar()
    recipes.render(
        st.session_state.user,
        get_recipe_repo(),
        get_food_database(),
        get_catalog_repo(),
        get_calorie_calculator(),
    )


def pantry_page_entry() -> None:
    from web.views import pantry
    _render_sidebar()
    pantry.render(st.session_state.user, get_inventory_repo())


def weekly_plan_page_entry() -> None:
    from web.views import weekly_plan
    _render_sidebar()
    weekly_plan.render(st.session_state.user, get_meal_plan_repo(), get_recipe_repo())


def grocery_list_page_entry() -> None:
    from web.views import grocery_list
    _render_sidebar()
    grocery_list.render(
        st.session_state.user,
        get_meal_plan_repo(),
        get_recipe_repo(),
        get_inventory_repo(),
        get_grocery_service(),
    )


def today_page_entry() -> None:
    from web.views import today
    _render_sidebar()
    today.render(st.session_state.user, get_meal_plan_repo(), get_food_log_repo())


def profile_page_entry() -> None:
    from web.views import profile
    _render_sidebar()
    profile.render(st.session_state.user, get_user_repo(), get_body_composition_service())


def render_authenticated() -> None:
    pages = [
        st.Page(today_page_entry, title="Today", icon=":material/today:", default=True),
        st.Page(weekly_plan_page_entry, title="Weekly Plan", icon=":material/calendar_month:"),
        st.Page(grocery_list_page_entry, title="Grocery List", icon=":material/shopping_cart:"),
        st.Page(recipes_page_entry, title="Recipes", icon=":material/menu_book:"),
        st.Page(pantry_page_entry, title="Pantry", icon=":material/kitchen:"),
        st.Page(profile_page_entry, title="My Profile", icon=":material/person:"),
    ]
    pg = st.navigation(pages)
    pg.run()


# --- Entry ---------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Meal Planner", layout="centered")
    if "user" in st.session_state:
        render_authenticated()
    else:
        render_unauthenticated()


if __name__ == "__main__":
    main()
