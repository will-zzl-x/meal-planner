"""Tests for SQLiteFoodLogRepository."""
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent))

from core.domain.models import Ingredient, Recipe
from repositories.sqlite.food_log_repository import SQLiteFoodLogRepository
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
    food_log = SQLiteFoodLogRepository(db)

    h = households.create("Smiths")
    u = users.create_user("Alice", email="a@x.com", household_id=h.id, is_planner=True)
    r = recipes.save(Recipe(
        name="Bowl",
        ingredients=[Ingredient("rice", Decimal("1"), "cup")],
        base_servings=1, calories_per_serving=500,
    ), h.id, u.user_id)
    return food_log, plans, h.id, u.user_id, r


def test_log_planned_meal_creates_entry(tmp_path):
    food_log, plans, h_id, user_id, r = _setup(tmp_path)
    today = date.today()
    entry = plans.save_entry(h_id, r.id, today, 2, "lunch")

    log = food_log.log_planned_meal(user_id, entry.id, today, calories=1000)
    assert log.calories == 1000
    assert log.meal_plan_entry_id == entry.id
    assert log.description is None


def test_log_planned_meal_is_idempotent(tmp_path):
    food_log, plans, h_id, user_id, r = _setup(tmp_path)
    today = date.today()
    entry = plans.save_entry(h_id, r.id, today, 1, "lunch")

    a = food_log.log_planned_meal(user_id, entry.id, today, 500)
    b = food_log.log_planned_meal(user_id, entry.id, today, 500)
    assert a.id == b.id
    assert len(food_log.find_by_date(user_id, today)) == 1


def test_log_off_plan_allows_multiple_per_day(tmp_path):
    food_log, _, _, user_id, _ = _setup(tmp_path)
    today = date.today()

    food_log.log_off_plan(user_id, today, "Coffee", 50)
    food_log.log_off_plan(user_id, today, "Apple", 80)
    entries = food_log.find_by_date(user_id, today)
    assert len(entries) == 2
    assert sum(e.calories for e in entries) == 130


def test_log_off_plan_rejects_blank_description(tmp_path):
    food_log, _, _, user_id, _ = _setup(tmp_path)
    with pytest.raises(ValueError):
        food_log.log_off_plan(user_id, date.today(), "", 100)


def test_find_by_date_returns_empty_for_quiet_day(tmp_path):
    food_log, _, _, user_id, _ = _setup(tmp_path)
    assert food_log.find_by_date(user_id, date.today()) == []


def test_find_by_date_isolates_other_dates(tmp_path):
    food_log, _, _, user_id, _ = _setup(tmp_path)
    today = date.today()
    yesterday = today - timedelta(days=1)
    food_log.log_off_plan(user_id, today, "Coffee", 50)
    food_log.log_off_plan(user_id, yesterday, "Tea", 5)

    assert len(food_log.find_by_date(user_id, today)) == 1
    assert len(food_log.find_by_date(user_id, yesterday)) == 1


def test_delete_log_entry(tmp_path):
    food_log, _, _, user_id, _ = _setup(tmp_path)
    today = date.today()
    entry = food_log.log_off_plan(user_id, today, "Coffee", 50)

    assert food_log.delete(entry.id, user_id) is True
    assert food_log.find_by_date(user_id, today) == []
    assert food_log.delete(entry.id, user_id) is False


def test_two_users_logs_isolated(tmp_path):
    db = str(tmp_path / "test.db")
    households = SQLiteHouseholdRepository(db)
    users = SQLiteUserRepository(db)
    food_log = SQLiteFoodLogRepository(db)
    h = households.create("Smiths")
    alice = users.create_user("Alice", email="a@x.com", household_id=h.id)
    bob = users.create_user("Bob", email="b@x.com", household_id=h.id)

    today = date.today()
    food_log.log_off_plan(alice.user_id, today, "Apple", 80)
    food_log.log_off_plan(bob.user_id, today, "Banana", 100)

    assert [e.calories for e in food_log.find_by_date(alice.user_id, today)] == [80]
    assert [e.calories for e in food_log.find_by_date(bob.user_id, today)] == [100]
