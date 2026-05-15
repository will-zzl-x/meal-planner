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

# Streamlit Cloud delivers secrets via st.secrets, not env vars. Copy any
# DATABASE_URL secret into the environment so the existing env-based fallback
# chain (DATABASE_URL > MEAL_PLANNER_DB > default file) keeps working both
# on Streamlit Cloud and on a plain local run.
try:
    if "DATABASE_URL" in st.secrets:
        os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
except Exception:
    pass  # local dev without a secrets.toml — env vars / default file are fine

from core.services.auth_service import (  # noqa: E402
    AuthService,
    EmailAlreadyRegisteredError,
    HouseholdNotFoundError,
)
from core.services.flexible_dieting import BodyCompositionService  # noqa: E402
from core.services.food_database_service import FoodDatabaseService  # noqa: E402
from core.services.grocery_list_service import GroceryListService  # noqa: E402
from core.services.pantry_coverage_service import PantryCoverageService  # noqa: E402
from core.services.recipe_calorie_calculator import RecipeCalorieCalculator  # noqa: E402
from core.services.seed_recipe_backfiller import SeedRecipeBackfiller  # noqa: E402
from repositories.sqlite.food_log_repository import SQLiteFoodLogRepository  # noqa: E402
from repositories.sqlite.household_repository import SQLiteHouseholdRepository  # noqa: E402
from repositories.sqlite.ingredient_catalog_repository import (  # noqa: E402
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository  # noqa: E402
from repositories.sqlite.meal_plan_repository import SQLiteMealPlanRepository  # noqa: E402
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository  # noqa: E402
from repositories.sqlite.user_repository import SQLiteUserRepository  # noqa: E402


# DATABASE_URL wins (production: Neon Postgres URL). Otherwise fall back to
# MEAL_PLANNER_DB (a SQLite file path) or the default local file.
DB_PATH = os.environ.get("DATABASE_URL") or os.environ.get("MEAL_PLANNER_DB", "meal_planner.db")


# --- Cached singletons ----------------------------------------------------

@st.cache_resource
def get_auth_service() -> AuthService:
    recipe_repo = SQLiteRecipeRepository(DB_PATH)
    catalog_repo = SQLiteIngredientCatalogRepository(DB_PATH)
    food_db = FoodDatabaseService()
    return AuthService(
        user_repo=SQLiteUserRepository(DB_PATH),
        household_repo=SQLiteHouseholdRepository(DB_PATH),
        recipe_repo=recipe_repo,           # auto-seeds new households
        # Auto-backfill seeded recipes so calorie figures are real on
        # day one. The backfiller is best-effort; AuthService swallows
        # any error so registration never fails because of network.
        backfiller=SeedRecipeBackfiller(food_db, catalog_repo, recipe_repo),
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


@st.cache_resource
def get_coverage_service() -> PantryCoverageService:
    return PantryCoverageService(get_inventory_repo(), get_catalog_repo())


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
    with st.spinner("Signing you in..."):
        user = get_auth_service().login(email, password)
    if user is None:
        st.error("Invalid email or password.")
        return
    st.session_state.user = user
    st.session_state.welcome_toast = f"Welcome back, {user.name}!"
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
        with st.spinner("Setting up your household and starter recipes — this takes a few seconds..."):
            result = get_auth_service().register_household(
                planner_name, email, password, household_name,
            )
    except EmailAlreadyRegisteredError:
        st.error("An account with that email already exists.")
        return
    except Exception as exc:
        st.error(f"Couldn't create the household: {exc}")
        return
    st.session_state.user = result.user
    st.session_state.welcome_toast = (
        f"Household '{result.household.name}' created. Welcome, {result.user.name}!"
    )
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
        with st.spinner("Joining the household..."):
            user = get_auth_service().register_member(name, email, password, invite_code)
    except HouseholdNotFoundError:
        st.error("That invite code doesn't match any household. Double-check it with the planner.")
        return
    except EmailAlreadyRegisteredError:
        st.error("An account with that email already exists.")
        return
    except Exception as exc:
        st.error(f"Couldn't join the household: {exc}")
        return
    st.session_state.user = user
    st.session_state.welcome_toast = f"Welcome to the household, {user.name}!"
    st.rerun()


_EVERYBITE_CSS = """
<style>
/* EveryBite structural polish — paired with the palette in .streamlit/config.toml.
   Kept narrow on purpose: rules target Streamlit's stable wrappers, not deep
   internals that get renamed across versions. */

/* Tighter, more confident headings. */
h1 { font-weight: 700; letter-spacing: -0.02em; }
h2, h3 { font-weight: 600; letter-spacing: -0.01em; }

/* Buttons: rounded, with weight. */
div.stButton > button,
div.stDownloadButton > button,
button[kind="primary"],
button[kind="secondary"] {
    border-radius: 10px;
    font-weight: 600;
    padding: 0.45rem 1rem;
}

/* Subtle card feel on bordered containers (Streamlit's `border=True` option). */
[data-testid="stExpander"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 12px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

/* Sidebar: a hairline edge so it reads as a separate surface. */
section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(15, 23, 42, 0.08);
}

/* Inputs: slightly softer corners. */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
textarea {
    border-radius: 8px !important;
}
</style>
"""


def render_unauthenticated() -> None:
    st.title("EveryBite")
    st.caption("Meal planning that fits your week.")
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
        get_coverage_service(),
    )


def pantry_page_entry() -> None:
    from web.views import pantry
    _render_sidebar()
    pantry.render(
        st.session_state.user,
        get_inventory_repo(),
        get_food_database(),
        get_catalog_repo(),
    )


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
    today.render(
        st.session_state.user,
        get_meal_plan_repo(),
        get_food_log_repo(),
        get_food_database(),
        get_catalog_repo(),
    )


def profile_page_entry() -> None:
    # Kept as a thin shim so old bookmarks / session links continue to work,
    # but Profile + Household now live under Settings.
    settings_page_entry()


def household_page_entry() -> None:
    settings_page_entry()


def settings_page_entry() -> None:
    from web.views import settings
    _render_sidebar()
    settings.render(
        st.session_state.user,
        get_user_repo(),
        get_body_composition_service(),
        get_household_repo(),
        get_user_repo(),
    )


def render_authenticated() -> None:
    # Cross-rerun toast: set during login / registration; consumed once here so
    # the user sees a confirmation after we navigate them to the Today page.
    toast = st.session_state.pop("welcome_toast", None)
    if toast:
        st.toast(toast, icon=":material/check_circle:")
    page_registry = {
        "today": st.Page(today_page_entry, title="Today", icon=":material/today:", default=True),
        "plan": st.Page(weekly_plan_page_entry, title="Plan", icon=":material/calendar_month:"),
        "groceries": st.Page(grocery_list_page_entry, title="Groceries", icon=":material/shopping_cart:"),
        "recipes": st.Page(recipes_page_entry, title="Recipes", icon=":material/menu_book:"),
        "pantry": st.Page(pantry_page_entry, title="Pantry", icon=":material/kitchen:"),
        "settings": st.Page(settings_page_entry, title="Settings", icon=":material/settings:"),
    }
    # Expose to views so empty-state CTAs can `page_link` across the app.
    from web.navigation import set_pages
    set_pages(page_registry)
    pg = st.navigation(list(page_registry.values()))
    pg.run()


# --- Entry ---------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="EveryBite", page_icon=":material/restaurant:", layout="centered")
    st.markdown(_EVERYBITE_CSS, unsafe_allow_html=True)
    if "user" in st.session_state:
        render_authenticated()
    else:
        render_unauthenticated()


if __name__ == "__main__":
    main()
