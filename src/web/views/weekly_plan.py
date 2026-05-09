"""
Weekly Plan view: 7 days at a glance with daily calorie totals. Planner can
add and remove meal slots; members see the same plan read-only.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List

import streamlit as st

from core.interfaces.meal_plan_repository import MealPlanEntry
from core.interfaces.user_repository import UserProfile
from repositories.sqlite.meal_plan_repository import SQLiteMealPlanRepository
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository


_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def render(user: UserProfile,
           plan_repo: SQLiteMealPlanRepository,
           recipe_repo: SQLiteRecipeRepository) -> None:
    st.title("Weekly Plan")
    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    monday = _current_week_monday()

    col_prev, col_today, col_next = st.columns(3)
    if col_prev.button("◀ Previous week"):
        st.session_state.week_offset = st.session_state.get("week_offset", 0) - 1
        st.rerun()
    if col_today.button("This week"):
        st.session_state.week_offset = 0
        st.rerun()
    if col_next.button("Next week ▶"):
        st.session_state.week_offset = st.session_state.get("week_offset", 0) + 1
        st.rerun()

    st.subheader(f"Week of {monday.strftime('%b %d, %Y')}")

    entries_by_day = _group_by_day(plan_repo.find_by_week(user.household_id, monday))
    for offset in range(7):
        day = monday + timedelta(days=offset)
        _render_day(user, plan_repo, day, _DAY_NAMES[offset], entries_by_day.get(day, []))

    if user.is_planner:
        st.divider()
        _render_add_meal_form(user, monday, plan_repo, recipe_repo)


def _current_week_monday() -> date:
    """Monday of the week the user is browsing (offset by st.session_state.week_offset)."""
    today = date.today()
    monday_of_today = today - timedelta(days=today.weekday())
    offset = st.session_state.get("week_offset", 0)
    return monday_of_today + timedelta(weeks=offset)


def _group_by_day(entries: List[MealPlanEntry]) -> Dict[date, List[MealPlanEntry]]:
    grouped: Dict[date, List[MealPlanEntry]] = defaultdict(list)
    for e in entries:
        grouped[e.planned_date].append(e)
    return grouped


def _render_day(user: UserProfile,
                plan_repo: SQLiteMealPlanRepository,
                day: date,
                day_name: str,
                entries: List[MealPlanEntry]) -> None:
    day_total = sum(e.planned_servings * (e.calories_per_serving or 0) for e in entries)
    st.markdown(f"### {day_name} · {day.strftime('%b %d')} — {day_total} cal")

    if not entries:
        st.caption("Nothing planned.")
        return

    for meal in _MEAL_TYPES:
        meal_entries = [e for e in entries if e.meal_type == meal]
        if not meal_entries:
            continue
        st.write(f"**{meal.capitalize()}**")
        for e in meal_entries:
            cal = e.planned_servings * (e.calories_per_serving or 0)
            cols = st.columns([5, 1])
            cols[0].write(f"• {e.recipe_name} × {e.planned_servings}  ·  {cal} cal")
            if user.is_planner:
                if cols[1].button("Remove", key=f"rm-{e.id}", type="secondary"):
                    plan_repo.delete_entry(e.id, user.household_id)
                    st.rerun()


def _render_add_meal_form(user: UserProfile,
                          monday: date,
                          plan_repo: SQLiteMealPlanRepository,
                          recipe_repo: SQLiteRecipeRepository) -> None:
    recipes = recipe_repo.find_all_by_household(user.household_id)
    if not recipes:
        st.info("Add some recipes first — there's nothing to plan with yet.")
        return

    st.subheader("Add a meal")
    with st.form("add_meal", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            day_choices = [monday + timedelta(days=i) for i in range(7)]
            day = st.selectbox(
                "Day", day_choices,
                format_func=lambda d: d.strftime("%A, %b %d"),
            )
            meal_type = st.selectbox("Meal", _MEAL_TYPES)
        with col2:
            recipe = st.selectbox(
                "Recipe", recipes,
                format_func=lambda r: f"{r.name} ({r.calories_per_serving} cal/serving)",
            )
            servings = st.number_input("Servings", min_value=1, max_value=20, value=1, step=1)
        submit = st.form_submit_button("Add to plan")

    if not submit:
        return
    plan_repo.save_entry(
        household_id=user.household_id,
        recipe_id=recipe.id,
        planned_date=day,
        planned_servings=int(servings),
        meal_type=meal_type,
    )
    st.success(f"Added {recipe.name} to {day.strftime('%A')} {meal_type}.")
    st.rerun()
