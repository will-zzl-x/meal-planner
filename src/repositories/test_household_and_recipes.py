"""
Smoke tests for SQLiteHouseholdRepository and SQLiteRecipeRepository against the
real migration-built schema. The recipe repo is household-scoped, so these tests
build a household first, then verify recipes are isolated to it.
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.domain.models import Recipe, Ingredient
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository
from repositories.sqlite.user_repository import SQLiteUserRepository


def _setup(tmp_path):
    db_path = str(tmp_path / "test.db")
    households = SQLiteHouseholdRepository(db_path)
    users = SQLiteUserRepository(db_path)
    recipes = SQLiteRecipeRepository(db_path)
    return households, users, recipes


def _sample_recipe(name: str = "Chicken bowl") -> Recipe:
    return Recipe(
        name=name,
        ingredients=[
            Ingredient(name="chicken breast", quantity=Decimal("6"), unit="oz"),
            Ingredient(name="rice", quantity=Decimal("1"), unit="cup"),
        ],
        base_servings=1,
        calories_per_serving=500,
    )


def test_household_create_and_lookup(tmp_path):
    households, _, _ = _setup(tmp_path)
    h = households.create("The Smiths")
    assert h.id
    assert h.name == "The Smiths"
    assert households.find_by_id(h.id) == h


def test_household_lists_member_user_ids(tmp_path):
    households, users, _ = _setup(tmp_path)
    h = households.create("The Smiths")
    a = users.create_user("Alice", "alice@example.com", household_id=h.id, is_planner=True)
    b = users.create_user("Bob", "bob@example.com", household_id=h.id)

    members = households.list_member_ids(h.id)
    assert set(members) == {a.user_id, b.user_id}


def test_recipe_save_and_find_within_household(tmp_path):
    households, users, recipes = _setup(tmp_path)
    h = households.create("The Smiths")
    alice = users.create_user("Alice", "alice@example.com", household_id=h.id, is_planner=True)

    saved = recipes.save(_sample_recipe(), household_id=h.id, created_by_user_id=alice.user_id)
    assert saved.name == "Chicken bowl"

    found = recipes.find_by_name("Chicken bowl", household_id=h.id)
    assert found is not None
    assert {ing.name for ing in found.ingredients} == {"chicken breast", "rice"}


def test_recipes_are_isolated_per_household(tmp_path):
    households, users, recipes = _setup(tmp_path)
    h1 = households.create("Smiths")
    h2 = households.create("Joneses")

    alice = users.create_user("Alice", "a@example.com", household_id=h1.id, is_planner=True)
    bob = users.create_user("Bob", "b@example.com", household_id=h2.id, is_planner=True)

    recipes.save(_sample_recipe("Smith special"), household_id=h1.id, created_by_user_id=alice.user_id)
    recipes.save(_sample_recipe("Jones special"), household_id=h2.id, created_by_user_id=bob.user_id)

    smith_names = {r.name for r in recipes.find_all_by_household(h1.id)}
    jones_names = {r.name for r in recipes.find_all_by_household(h2.id)}
    assert smith_names == {"Smith special"}
    assert jones_names == {"Jones special"}


def test_recipe_metadata_roundtrips(tmp_path):
    """Recipe.instructions / notes / tier and Ingredient.store all persist."""
    households, users, recipes = _setup(tmp_path)
    h = households.create("Smiths")
    alice = users.create_user("Alice", "a@example.com", household_id=h.id, is_planner=True)

    rich = Recipe(
        name="Tagged recipe",
        ingredients=[
            Ingredient(name="chicken breast", quantity=Decimal("6"), unit="oz", store="Costco"),
            Ingredient(name="rice", quantity=Decimal("1"), unit="cup", store="Walmart"),
        ],
        base_servings=1,
        calories_per_serving=400,
        instructions=["Chop everything", "Cook it"],
        notes="A note with [chips] and full sentences.",
        tier="A",
    )
    recipes.save(rich, household_id=h.id, created_by_user_id=alice.user_id)

    reloaded = recipes.find_by_name("Tagged recipe", household_id=h.id)
    assert reloaded is not None
    assert reloaded.tier == "A"
    assert reloaded.notes == "A note with [chips] and full sentences."
    assert reloaded.instructions == ["Chop everything", "Cook it"]
    by_name = {ing.name: ing for ing in reloaded.ingredients}
    assert by_name["chicken breast"].store == "Costco"
    assert by_name["rice"].store == "Walmart"


def test_user_password_and_planner_flag_persist(tmp_path):
    households, users, _ = _setup(tmp_path)
    h = households.create("The Smiths")
    alice = users.create_user(
        "Alice", "alice@example.com",
        password_hash="not-a-real-hash",
        household_id=h.id, is_planner=True,
    )

    reloaded = users.find_by_email("alice@example.com")
    assert reloaded is not None
    assert reloaded.user_id == alice.user_id
    assert reloaded.password_hash == "not-a-real-hash"
    assert reloaded.is_planner is True
    assert reloaded.household_id == h.id

    assert users.update_password_hash(alice.user_id, "new-hash") is True
    assert users.find_by_id(alice.user_id).password_hash == "new-hash"
