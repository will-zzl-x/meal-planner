"""Tests for SQLiteMealPlanRepository."""
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent))

from core.domain.models import Ingredient, Recipe
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.meal_plan_repository import SQLiteMealPlanRepository
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository
from repositories.sqlite.user_repository import SQLiteUserRepository


def _setup(tmp_path):
    db = str(tmp_path / "test.db")
    households = SQLiteHouseholdRepository(db)
    users = SQLiteUserRepository(db)
    recipes = SQLiteRecipeRepository(db)
    plans = SQLiteMealPlanRepository(db)

    h = households.create("Smiths")
    u = users.create_user("Alice", email="a@x.com", household_id=h.id, is_planner=True)
    r1 = recipes.save(_recipe("Chicken bowl", 500), h.id, u.user_id)
    r2 = recipes.save(_recipe("Oatmeal", 300), h.id, u.user_id)
    return plans, h.id, r1, r2


def _recipe(name: str, calories: int) -> Recipe:
    return Recipe(
        name=name,
        ingredients=[Ingredient("chicken breast", Decimal("6"), "oz")],
        base_servings=1,
        calories_per_serving=calories,
    )


def _monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def test_empty_week_returns_no_entries(tmp_path):
    plans, h_id, _, _ = _setup(tmp_path)
    assert plans.find_by_week(h_id, _monday()) == []


def test_save_and_find_entry(tmp_path):
    plans, h_id, r1, _ = _setup(tmp_path)
    monday = _monday()

    saved = plans.save_entry(h_id, r1.id, monday, planned_servings=2, meal_type="lunch")
    assert saved.id
    assert saved.recipe_id == r1.id
    assert saved.recipe_name == "Chicken bowl"
    assert saved.calories_per_serving == 500
    assert saved.planned_servings == 2
    assert saved.meal_type == "lunch"

    entries = plans.find_by_week(h_id, monday)
    assert len(entries) == 1
    assert entries[0].id == saved.id


def test_save_entry_replaces_servings_for_same_slot(tmp_path):
    plans, h_id, r1, _ = _setup(tmp_path)
    monday = _monday()

    plans.save_entry(h_id, r1.id, monday, planned_servings=1, meal_type="lunch")
    plans.save_entry(h_id, r1.id, monday, planned_servings=4, meal_type="lunch")

    entries = plans.find_by_week(h_id, monday)
    assert len(entries) == 1
    assert entries[0].planned_servings == 4


def test_same_recipe_different_meal_types_coexist(tmp_path):
    plans, h_id, r1, _ = _setup(tmp_path)
    monday = _monday()

    plans.save_entry(h_id, r1.id, monday, planned_servings=1, meal_type="lunch")
    plans.save_entry(h_id, r1.id, monday, planned_servings=1, meal_type="dinner")

    assert len(plans.find_by_week(h_id, monday)) == 2


def test_find_by_date_orders_by_meal_type(tmp_path):
    plans, h_id, r1, r2 = _setup(tmp_path)
    monday = _monday()

    plans.save_entry(h_id, r1.id, monday, planned_servings=1, meal_type="dinner")
    plans.save_entry(h_id, r2.id, monday, planned_servings=1, meal_type="breakfast")
    plans.save_entry(h_id, r1.id, monday, planned_servings=1, meal_type="lunch")

    types = [e.meal_type for e in plans.find_by_date(h_id, monday)]
    assert types == ["breakfast", "lunch", "dinner"]


def test_delete_entry(tmp_path):
    plans, h_id, r1, _ = _setup(tmp_path)
    monday = _monday()

    saved = plans.save_entry(h_id, r1.id, monday, planned_servings=1, meal_type="lunch")
    assert plans.delete_entry(saved.id, h_id) is True
    assert plans.find_by_week(h_id, monday) == []
    assert plans.delete_entry(saved.id, h_id) is False


def test_clear_week_only_clears_in_range(tmp_path):
    plans, h_id, r1, _ = _setup(tmp_path)
    this_monday = _monday()
    next_monday = this_monday + timedelta(days=7)

    plans.save_entry(h_id, r1.id, this_monday, 1, "lunch")
    plans.save_entry(h_id, r1.id, this_monday + timedelta(days=3), 1, "lunch")
    plans.save_entry(h_id, r1.id, next_monday, 1, "lunch")

    removed = plans.clear_week(h_id, this_monday)
    assert removed == 2
    assert plans.find_by_week(h_id, this_monday) == []
    assert len(plans.find_by_week(h_id, next_monday)) == 1


def test_save_rejects_invalid_meal_type(tmp_path):
    plans, h_id, r1, _ = _setup(tmp_path)
    with pytest.raises(ValueError):
        plans.save_entry(h_id, r1.id, _monday(), 1, "second_breakfast")


def test_save_rejects_zero_servings(tmp_path):
    plans, h_id, r1, _ = _setup(tmp_path)
    with pytest.raises(ValueError):
        plans.save_entry(h_id, r1.id, _monday(), 0, "lunch")
