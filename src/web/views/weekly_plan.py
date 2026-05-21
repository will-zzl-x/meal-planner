"""
Weekly Plan view: shows the household's active planning cycle day by day,
with calorie totals per day. Planners can add/remove meals and create new
cycles; members see the same plan read-only.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional

import streamlit as st

from core.interfaces.cycle_repository import Cycle, ICycleRepository
from core.interfaces.meal_plan_repository import MealPlanEntry
from core.interfaces.user_repository import UserProfile
from repositories.sqlite.cycle_repository import SQLiteCycleRepository
from repositories.sqlite.meal_plan_repository import SQLiteMealPlanRepository
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository


_MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def render(user: UserProfile,
           plan_repo: SQLiteMealPlanRepository,
           recipe_repo: SQLiteRecipeRepository,
           cycle_repo: ICycleRepository) -> None:
    st.title("Plan")
    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    cycle = cycle_repo.find_active(user.household_id)

    if cycle is None:
        _render_no_cycle(user, cycle_repo)
        return

    _render_cycle_header(user, cycle, cycle_repo)

    entries_by_day = _group_by_day(
        plan_repo.find_by_date_range(user.household_id, cycle.start_date, cycle.end_date)
    )
    days = _days_in_range(cycle.start_date, cycle.end_date)
    for day in days:
        _render_day(user, plan_repo, day, entries_by_day.get(day, []))

    if user.is_planner:
        st.divider()
        _render_add_meal_form(user, cycle, plan_repo, recipe_repo)


# ------------------------------------------------------------------ helpers

def _days_in_range(start: date, end: date) -> List[date]:
    delta = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(delta)]


def _group_by_day(entries: List[MealPlanEntry]) -> Dict[date, List[MealPlanEntry]]:
    grouped: Dict[date, List[MealPlanEntry]] = defaultdict(list)
    for e in entries:
        grouped[e.planned_date].append(e)
    return grouped


# ------------------------------------------------------------------ sub-renders

def _render_no_cycle(user: UserProfile, cycle_repo: ICycleRepository) -> None:
    st.info("No active planning cycle yet.")
    if user.is_planner:
        st.caption("Create a cycle to start planning your meals.")
        _render_create_cycle_form(user, cycle_repo)
    else:
        st.caption("Ask your planner to set up a cycle.")


def _render_cycle_header(user: UserProfile,
                         cycle: Cycle,
                         cycle_repo: ICycleRepository) -> None:
    col_label, col_btn = st.columns([3, 1])
    col_label.subheader(cycle.label)
    if user.is_planner:
        if col_btn.button("New cycle", type="secondary"):
            st.session_state["show_new_cycle_form"] = True

    if st.session_state.get("show_new_cycle_form"):
        with st.expander("Start a new cycle", expanded=True):
            _render_create_cycle_form(user, cycle_repo)


def _render_create_cycle_form(user: UserProfile,
                              cycle_repo: ICycleRepository) -> None:
    today = date.today()
    with st.form("create_cycle", clear_on_submit=True):
        col1, col2 = st.columns(2)
        start = col1.date_input("Start date", value=today)
        end = col2.date_input("End date", value=today + timedelta(days=6))
        submit = st.form_submit_button("Start cycle", type="primary")
    if submit:
        if end < start:
            st.error("End date must be on or after the start date.")
            return
        cycle_repo.create(user.household_id, start, end)
        st.session_state.pop("show_new_cycle_form", None)
        st.rerun()


def _render_day(user: UserProfile,
                plan_repo: SQLiteMealPlanRepository,
                day: date,
                entries: List[MealPlanEntry]) -> None:
    is_today = day == date.today()
    day_label = day.strftime("%A · %b %d")
    if is_today:
        day_label += " · **Today**"
    day_total = sum(e.planned_servings * (e.calories_per_serving or 0) for e in entries)
    st.markdown(f"### {day_label} — {day_total} cal")

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
            cols = st.columns([4, 2])
            cols[0].write(f"• {e.recipe_name} × {e.planned_servings}  ·  {cal} cal")
            if user.is_planner:
                if cols[1].button("Remove", key=f"rm-{e.id}", type="secondary",
                                  use_container_width=True):
                    plan_repo.delete_entry(e.id, user.household_id)
                    st.rerun()


def _render_add_meal_form(user: UserProfile,
                          cycle: Cycle,
                          plan_repo: SQLiteMealPlanRepository,
                          recipe_repo: SQLiteRecipeRepository) -> None:
    recipes = recipe_repo.find_all_by_household(user.household_id)
    if not recipes:
        st.info("No recipes yet — nothing to plan with.")
        from web.navigation import page as nav_page
        if (recipes_pg := nav_page("recipes")):
            st.page_link(recipes_pg, label="Add a recipe", icon=":material/menu_book:")
        return

    st.subheader("Add a meal")
    with st.form("add_meal", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            day_choices = _days_in_range(cycle.start_date, cycle.end_date)
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
