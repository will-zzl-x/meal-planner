"""
Grocery List view: shows what's still needed to cook this week's plan, after
subtracting what's already in the pantry. Members see read-only; the planner
sees the same view (no edits to make on this page).
"""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from core.interfaces.user_repository import UserProfile
from core.services.grocery_list_service import GroceryListService
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository
from repositories.sqlite.meal_plan_repository import SQLiteMealPlanRepository
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository


def render(user: UserProfile,
           plan_repo: SQLiteMealPlanRepository,
           recipe_repo: SQLiteRecipeRepository,
           inventory_repo: SQLiteInventoryRepository,
           grocery_service: GroceryListService) -> None:
    from web.navigation import page as nav_page
    st.title("Groceries")
    st.caption("Everything you still need to cook this week's meals.")
    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    _render_pantry_freshness_banner(user, inventory_repo)

    monday = _current_week_monday()
    st.caption(f"For week of {monday.strftime('%b %d, %Y')} (switch weeks on the Plan page)")

    entries = plan_repo.find_by_week(user.household_id, monday)
    if not entries:
        st.info("No meals planned this week yet.")
        if (plan := nav_page("plan")):
            st.page_link(plan, label="Plan this week", icon=":material/calendar_month:")
        return

    recipes_by_id = {r.id: r for r in recipe_repo.find_all_by_household(user.household_id)}
    pantry = inventory_repo.get_household_inventory(user.household_id)
    items = grocery_service.generate(entries, recipes_by_id, pantry)

    if not items:
        st.success("Your pantry already covers everything you've planned this week!")
        if (pantry_pg := nav_page("pantry")):
            st.page_link(pantry_pg, label="Open the Pantry", icon=":material/kitchen:")
        return

    st.write(f"**{len(items)} item(s) to buy:**")
    for item in items:
        st.write(f"- {item.name} — **{item.actual_need} {item.unit}**")

    # Plain text block for easy copy-paste into a notes app or message.
    plain = "\n".join(f"{i.actual_need} {i.unit} {i.name}" for i in items)
    with st.expander("Copy as text"):
        st.code(plain, language="text")


def _current_week_monday() -> date:
    today = date.today()
    monday_of_today = today - timedelta(days=today.weekday())
    offset = st.session_state.get("week_offset", 0)
    return monday_of_today + timedelta(weeks=offset)


def _render_pantry_freshness_banner(user: UserProfile,
                                    inventory_repo: SQLiteInventoryRepository) -> None:
    """If the pantry hasn't been reviewed in >3 days, surface a warning.
    The grocery list subtracts pantry inventory, so a stale pantry
    silently makes the list wrong (showing items you actually have)."""
    from web.navigation import page as nav_page
    last = inventory_repo.last_reviewed_at(user.household_id)
    if last is None:
        st.warning(
            "Pantry has never been reviewed. The list below assumes you "
            "have nothing on hand — open the Pantry first to log what you "
            "already have."
        )
        if (pantry := nav_page("pantry")):
            st.page_link(pantry, label="Open the Pantry", icon=":material/kitchen:")
        return
    days = _days_since(last)
    if days > 3:
        st.warning(
            f"Last pantry check-in was {days} days ago. The grocery list "
            "may be off until you confirm what you still have."
        )
        if (pantry := nav_page("pantry")):
            st.page_link(pantry, label="Quick check-in", icon=":material/kitchen:")
    else:
        st.caption(f"_Pantry checked {days} day(s) ago._")


def _days_since(ts) -> int:
    from datetime import datetime
    return max(0, (datetime.now() - ts).days)
