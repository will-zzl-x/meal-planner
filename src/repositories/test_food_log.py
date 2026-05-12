"""Tests for SQLiteFoodLogRepository (migration 007)."""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.domain.models import Ingredient, Recipe
from repositories.sqlite.food_log_repository import SQLiteFoodLogRepository
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.meal_plan_repository import SQLiteMealPlanRepository
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository
from repositories.sqlite.user_repository import SQLiteUserRepository


def _setup(tmp_path):
    db = str(tmp_path / "log.db")
    households = SQLiteHouseholdRepository(db)
    users = SQLiteUserRepository(db)
    log = SQLiteFoodLogRepository(db)
    plans = SQLiteMealPlanRepository(db)
    recipes = SQLiteRecipeRepository(db)
    h = households.create("Smiths")
    alice = users.create_user("Alice", "a@example.com", household_id=h.id)
    bob = users.create_user("Bob", "b@example.com", household_id=h.id)
    return log, alice, bob, plans, recipes, h


def _seed_planned_meal(plans, recipes, household_id, user_id,
                       day: date, recipe_name: str = "R") -> str:
    """Create a real meal_plans row so log_planned_meal's FK is satisfied."""
    r = recipes.save(Recipe(
        name=recipe_name,
        ingredients=[Ingredient(name="x", quantity=Decimal("1"), unit="100g")],
        base_servings=1, calories_per_serving=300,
    ), household_id=household_id, created_by_user_id=user_id)
    entry = plans.save_entry(household_id, r.id, day, 1, "lunch")
    return entry.id


def test_log_off_plan_persists_and_reads_back(tmp_path):
    log, alice, _, _, _, _ = _setup(tmp_path)
    today = date(2026, 5, 10)
    entry = log.log_off_plan(alice.user_id, today, "Granola bar", 200)
    assert entry.id
    assert entry.calories == 200
    assert entry.description == "Granola bar"
    assert entry.meal_plan_entry_id is None

    [reloaded] = log.find_by_date(alice.user_id, today)
    assert reloaded.id == entry.id


def test_log_planned_meal_is_idempotent(tmp_path):
    """Two ticks on the same planned meal should result in one entry,
    not two."""
    log, alice, _, plans, recipes, h = _setup(tmp_path)
    today = date(2026, 5, 10)
    plan_id = _seed_planned_meal(plans, recipes, h.id, alice.user_id, today)
    a = log.log_planned_meal(alice.user_id, plan_id, today, 500)
    b = log.log_planned_meal(alice.user_id, plan_id, today, 500)
    assert a.id == b.id
    entries = log.find_by_date(alice.user_id, today)
    assert len(entries) == 1


def test_find_by_date_filters_by_user(tmp_path):
    """Alice's log shouldn't include Bob's entries on the same day."""
    log, alice, bob, _, _, _ = _setup(tmp_path)
    today = date(2026, 5, 10)
    log.log_off_plan(alice.user_id, today, "Apple", 80)
    log.log_off_plan(bob.user_id, today, "Toast", 120)
    alice_entries = log.find_by_date(alice.user_id, today)
    assert [e.description for e in alice_entries] == ["Apple"]


def test_find_by_date_filters_by_date(tmp_path):
    log, alice, _, _, _, _ = _setup(tmp_path)
    log.log_off_plan(alice.user_id, date(2026, 5, 10), "Today", 100)
    log.log_off_plan(alice.user_id, date(2026, 5, 11), "Tomorrow", 200)
    today_entries = log.find_by_date(alice.user_id, date(2026, 5, 10))
    assert [e.description for e in today_entries] == ["Today"]


def test_delete_only_removes_own_entry(tmp_path):
    """A user can't delete another user's entries even with the right id."""
    log, alice, bob, _, _, _ = _setup(tmp_path)
    today = date(2026, 5, 10)
    bob_entry = log.log_off_plan(bob.user_id, today, "Bob's lunch", 600)
    # Alice tries to delete it — should fail.
    assert log.delete(bob_entry.id, alice.user_id) is False
    # Bob can still find it.
    assert log.find_by_date(bob.user_id, today)
    # Bob can delete his own.
    assert log.delete(bob_entry.id, bob.user_id) is True
    assert log.find_by_date(bob.user_id, today) == []
