"""Tests for SQLiteMealPlanRepository (migration 006)."""
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
    db = str(tmp_path / "mp.db")
    households = SQLiteHouseholdRepository(db)
    users = SQLiteUserRepository(db)
    recipes = SQLiteRecipeRepository(db)
    plans = SQLiteMealPlanRepository(db)
    h = households.create("Smiths")
    alice = users.create_user("Alice", "a@example.com",
                              household_id=h.id, is_planner=True)
    return h, alice, recipes, plans


def _seed_recipe(recipes, hid, uid, name="Chicken Bowl") -> str:
    r = recipes.save(Recipe(
        name=name,
        ingredients=[Ingredient(name="chicken", quantity=Decimal("1"), unit="100g")],
        base_servings=1,
        calories_per_serving=400,
    ), household_id=hid, created_by_user_id=uid)
    return r.id


def test_save_and_find_by_date(tmp_path):
    h, alice, recipes, plans = _setup(tmp_path)
    rid = _seed_recipe(recipes, h.id, alice.user_id)
    today = date(2026, 5, 10)
    plans.save_entry(h.id, rid, today, planned_servings=2, meal_type="lunch")

    entries = plans.find_by_date(h.id, today)
    assert len(entries) == 1
    assert entries[0].planned_servings == 2
    assert entries[0].meal_type == "lunch"
    assert entries[0].recipe_name == "Chicken Bowl"
    assert entries[0].calories_per_serving == 400


def test_save_replaces_existing_slot(tmp_path):
    """(household, date, recipe, meal_type) is a unique slot — saving the
    same combination again updates servings instead of creating duplicates."""
    h, alice, recipes, plans = _setup(tmp_path)
    rid = _seed_recipe(recipes, h.id, alice.user_id)
    today = date(2026, 5, 10)
    plans.save_entry(h.id, rid, today, 1, "lunch")
    plans.save_entry(h.id, rid, today, 3, "lunch")

    entries = plans.find_by_date(h.id, today)
    assert len(entries) == 1
    assert entries[0].planned_servings == 3


def test_find_by_week_filters_correctly(tmp_path):
    h, alice, recipes, plans = _setup(tmp_path)
    rid = _seed_recipe(recipes, h.id, alice.user_id)
    monday = date(2026, 5, 11)  # ISO week starts Mon
    plans.save_entry(h.id, rid, monday, 1, "breakfast")
    plans.save_entry(h.id, rid, monday + timedelta(days=3), 1, "dinner")
    # Outside the week (next Monday) — should not appear.
    plans.save_entry(h.id, rid, monday + timedelta(days=7), 1, "lunch")

    week_entries = plans.find_by_week(h.id, monday)
    assert len(week_entries) == 2


def test_delete_entry(tmp_path):
    h, alice, recipes, plans = _setup(tmp_path)
    rid = _seed_recipe(recipes, h.id, alice.user_id)
    entry = plans.save_entry(h.id, rid, date(2026, 5, 10), 1, "lunch")
    assert plans.delete_entry(entry.id, h.id) is True
    assert plans.delete_entry(entry.id, h.id) is False  # already gone
    assert plans.find_by_date(h.id, date(2026, 5, 10)) == []


def test_clear_week_returns_count(tmp_path):
    h, alice, recipes, plans = _setup(tmp_path)
    rid = _seed_recipe(recipes, h.id, alice.user_id)
    monday = date(2026, 5, 11)
    plans.save_entry(h.id, rid, monday, 1, "breakfast")
    plans.save_entry(h.id, rid, monday + timedelta(days=2), 1, "lunch")
    plans.save_entry(h.id, rid, monday + timedelta(days=8), 1, "lunch")  # next week

    cleared = plans.clear_week(h.id, monday)
    assert cleared == 2
    assert len(plans.find_by_week(h.id, monday)) == 0


def test_invalid_meal_type_rejected(tmp_path):
    h, alice, recipes, plans = _setup(tmp_path)
    rid = _seed_recipe(recipes, h.id, alice.user_id)
    with pytest.raises(ValueError):
        plans.save_entry(h.id, rid, date(2026, 5, 10), 1, "midnight_snack")


def test_zero_servings_rejected(tmp_path):
    h, alice, recipes, plans = _setup(tmp_path)
    rid = _seed_recipe(recipes, h.id, alice.user_id)
    with pytest.raises(ValueError):
        plans.save_entry(h.id, rid, date(2026, 5, 10), 0, "lunch")
