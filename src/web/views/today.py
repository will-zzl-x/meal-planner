"""
Today view: full day at a glance.

For each meal slot in today's household plan, the user sees a checkbox to mark
"I ate this." Ticked entries count toward today's logged calories. Below the
plan, an "Off-plan eating" form lets the user record snacks, restaurant meals,
or anything not on the plan.

Logging is per user — every household member maintains their own daily log.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List

import streamlit as st

from core.interfaces.food_log_repository import FoodLogEntry
from core.interfaces.meal_plan_repository import MealPlanEntry
from core.interfaces.user_repository import UserProfile
from repositories.sqlite.food_log_repository import SQLiteFoodLogRepository
from repositories.sqlite.meal_plan_repository import SQLiteMealPlanRepository


_MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]


def render(user: UserProfile,
           plan_repo: SQLiteMealPlanRepository,
           food_log_repo: SQLiteFoodLogRepository) -> None:
    st.title("Today")
    today = date.today()
    st.caption(today.strftime("%A, %B %d, %Y"))

    if not user.household_id:
        st.warning("You're not in a household yet. Ask the planner for an invite code.")
        return

    plan_entries = plan_repo.find_by_date(user.household_id, today)
    log_entries = food_log_repo.find_by_date(user.user_id, today)
    logged_by_plan_id = {e.meal_plan_entry_id: e for e in log_entries if e.meal_plan_entry_id}
    off_plan_entries = [e for e in log_entries if e.meal_plan_entry_id is None]

    _render_totals(user, log_entries)

    if plan_entries:
        st.divider()
        _render_planned_meals(user, plan_entries, logged_by_plan_id, food_log_repo, today)
    else:
        st.info("Nothing planned for today. Add planned meals on the Weekly Plan page, or log something off-plan below.")

    st.divider()
    _render_off_plan_section(user, off_plan_entries, food_log_repo, today)


def _render_totals(user: UserProfile, log_entries: List[FoodLogEntry]) -> None:
    logged = sum(e.calories for e in log_entries)
    target = user.daily_calorie_target
    cols = st.columns(3)
    cols[0].metric("Logged", f"{logged} cal")
    if target:
        cols[1].metric("Target", f"{target} cal")
        cols[2].metric("Remaining", f"{target - logged} cal")
    else:
        cols[1].metric("Target", "—")
        cols[2].caption("Set a target on My Profile to see remaining.")


def _render_planned_meals(user: UserProfile,
                          plan_entries: List[MealPlanEntry],
                          logged_by_plan_id: Dict[str, FoodLogEntry],
                          food_log_repo: SQLiteFoodLogRepository,
                          today: date) -> None:
    st.subheader("Planned meals")
    by_meal: Dict[str, List[MealPlanEntry]] = {m: [] for m in _MEAL_TYPES}
    for e in plan_entries:
        by_meal[e.meal_type].append(e)

    for meal_type in _MEAL_TYPES:
        meal_entries = by_meal[meal_type]
        if not meal_entries:
            continue
        st.write(f"**{meal_type.capitalize()}**")
        for entry in meal_entries:
            _render_planned_meal_row(user, entry, logged_by_plan_id, food_log_repo, today)


def _render_planned_meal_row(user: UserProfile,
                             entry: MealPlanEntry,
                             logged_by_plan_id: Dict[str, FoodLogEntry],
                             food_log_repo: SQLiteFoodLogRepository,
                             today: date) -> None:
    cal = entry.planned_servings * (entry.calories_per_serving or 0)
    label = f"{entry.recipe_name} × {entry.planned_servings}  ·  {cal} cal"
    is_logged = entry.id in logged_by_plan_id

    checked = st.checkbox(label, value=is_logged, key=f"tick-{entry.id}")
    if checked == is_logged:
        return  # No state change.

    if checked:
        food_log_repo.log_planned_meal(user.user_id, entry.id, today, cal)
    else:
        food_log_repo.delete(logged_by_plan_id[entry.id].id, user.user_id)
    st.rerun()


def _render_off_plan_section(user: UserProfile,
                             off_plan_entries: List[FoodLogEntry],
                             food_log_repo: SQLiteFoodLogRepository,
                             today: date) -> None:
    st.subheader("Off-plan eating")
    if off_plan_entries:
        for entry in off_plan_entries:
            cols = st.columns([5, 1])
            cols[0].write(f"• {entry.description} — **{entry.calories} cal**")
            if cols[1].button("Remove", key=f"off-rm-{entry.id}", type="secondary"):
                food_log_repo.delete(entry.id, user.user_id)
                st.rerun()
    else:
        st.caption("Nothing logged off-plan today.")

    with st.form("log_off_plan", clear_on_submit=True):
        col_desc, col_cal = st.columns([3, 1])
        with col_desc:
            description = st.text_input("What did you eat?").strip()
        with col_cal:
            calories = st.number_input("Calories", min_value=0, max_value=5000, value=0, step=10)
        submit = st.form_submit_button("Log it")

    if not submit:
        return
    if not description:
        st.error("Please describe what you ate.")
        return
    food_log_repo.log_off_plan(user.user_id, today, description, int(calories))
    st.rerun()
