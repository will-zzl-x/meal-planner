"""Tests for SeedRecipeBackfiller (slice 8e)."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import Ingredient, Recipe
from core.services.food_database_service import FoodDatabaseService
from core.services.seed_recipe_backfiller import (
    SeedRecipeBackfiller,
    _candidate_queries,
    _convert_to_servings,
    _strip_pending_marker,
)
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository
from repositories.sqlite.user_repository import SQLiteUserRepository


# ---------------------------------------------------- pure conversion logic

def test_oz_to_per100g_servings():
    # 6 oz / 100g → 6 × 28.35 / 100 = 1.701 servings
    s = _convert_to_servings(quantity=Decimal("6"), recipe_unit="oz",
                             catalog_serving_label="100g")
    assert s is not None
    assert abs(float(s) - 1.701) < 0.001


def test_lb_to_per100g_servings():
    s = _convert_to_servings(quantity=Decimal("1"), recipe_unit="lb",
                             catalog_serving_label="100g")
    assert abs(float(s) - 4.5359) < 0.001


def test_cup_assumes_240g():
    s = _convert_to_servings(quantity=Decimal("1"), recipe_unit="cup",
                             catalog_serving_label="100g")
    assert abs(float(s) - 2.4) < 0.001


def test_piece_unit_with_per_piece_catalog():
    s = _convert_to_servings(quantity=Decimal("4"), recipe_unit="eggs",
                             catalog_serving_label="piece")
    assert s == Decimal("4")


def test_piece_recipe_unit_with_g_catalog_fails():
    s = _convert_to_servings(quantity=Decimal("2"), recipe_unit="thighs",
                             catalog_serving_label="100g")
    assert s is None


def test_unknown_recipe_unit_returns_none():
    s = _convert_to_servings(quantity=Decimal("1"), recipe_unit="shake",
                             catalog_serving_label="100g")
    assert s is None


def test_label_with_explicit_grams_extracted():
    # "1 cup (227 g)" → catalog provides 227g per serving, recipe wants 1 cup (240g)
    # → 240/227 ≈ 1.057 servings
    s = _convert_to_servings(quantity=Decimal("1"), recipe_unit="cup",
                             catalog_serving_label="1 cup (227 g)")
    assert s is not None
    assert 1.0 < float(s) < 1.1


def test_strip_pending_marker_removes_and_tidies_whitespace():
    notes = "[Protein: Chicken]  [calories pending lookup]  cooking note here."
    assert _strip_pending_marker(notes) == "[Protein: Chicken] cooking note here."


def test_strip_pending_marker_no_marker_is_noop():
    notes = "Plain notes with no marker."
    assert _strip_pending_marker(notes) == notes


def test_backfill_strips_pending_marker_on_successful_match(tmp_path):
    households, users, catalog, recipes, backfiller = _setup(tmp_path)
    h = households.create("Smiths")
    alice = users.create_user("Alice", "a@example.com", household_id=h.id, is_planner=True)

    recipes.save(Recipe(
        name="Test bowl",
        ingredients=[Ingredient(name="chicken breast", quantity=Decimal("6"), unit="oz")],
        base_servings=1,
        calories_per_serving=0,
        notes="[Protein: Chicken]  [calories pending lookup]  Marinate overnight.",
    ), household_id=h.id, created_by_user_id=alice.user_id)

    backfiller.backfill_household(h.id)
    reloaded = recipes.find_all_by_household(h.id)[0]
    assert "[calories pending lookup]" not in reloaded.notes
    assert reloaded.notes == "[Protein: Chicken] Marinate overnight."


def test_candidate_queries_progressively_simpler():
    queries = _candidate_queries("Skinless chicken thighs (~4 thighs, ~32 oz)")
    assert "Skinless chicken thighs (~4 thighs, ~32 oz)" in queries
    assert any("chicken thighs" in q.lower() for q in queries)


# ---------------------------------------------------- end-to-end backfill

def _setup(tmp_path):
    db_path = str(tmp_path / "backfill.db")
    households = SQLiteHouseholdRepository(db_path)
    users = SQLiteUserRepository(db_path)
    catalog = SQLiteIngredientCatalogRepository(db_path)
    recipes = SQLiteRecipeRepository(db_path)
    food_db = FoodDatabaseService(network_enabled=False)  # offline sample only
    backfiller = SeedRecipeBackfiller(food_db, catalog, recipes)
    return households, users, catalog, recipes, backfiller


def test_backfills_legacy_recipe_with_resolvable_ingredients(tmp_path):
    households, users, catalog, recipes, backfiller = _setup(tmp_path)
    h = households.create("Smiths")
    alice = users.create_user("Alice", "a@example.com", household_id=h.id, is_planner=True)

    # Free-text ingredients matching the offline sample DB.
    recipes.save(Recipe(
        name="Test bowl",
        ingredients=[
            Ingredient(name="chicken breast", quantity=Decimal("6"), unit="oz"),
            Ingredient(name="white rice cooked", quantity=Decimal("1"), unit="cup"),
            Ingredient(name="salt", quantity=Decimal("0"), unit="tsp"),
        ],
        base_servings=1,
        calories_per_serving=0,
    ), household_id=h.id, created_by_user_id=alice.user_id)

    report = backfiller.backfill_household(h.id)
    assert report.total_recipes == 1
    assert report.total_ingredients_matched == 2  # chicken + rice
    assert report.total_ingredients_skipped == 1  # salt (qty 0)

    reloaded = recipes.find_all_by_household(h.id)[0]
    matched = [i for i in reloaded.ingredients if i.catalog_ingredient_id]
    assert len(matched) == 2
    # Calories should now reflect the matched ingredients.
    assert reloaded.calories_per_serving > 0


def test_backfill_is_idempotent(tmp_path):
    households, users, catalog, recipes, backfiller = _setup(tmp_path)
    h = households.create("Smiths")
    alice = users.create_user("Alice", "a@example.com", household_id=h.id, is_planner=True)

    recipes.save(Recipe(
        name="Just chicken",
        ingredients=[Ingredient(name="chicken breast", quantity=Decimal("6"), unit="oz")],
        base_servings=1,
        calories_per_serving=0,
    ), household_id=h.id, created_by_user_id=alice.user_id)

    first = backfiller.backfill_household(h.id)
    second = backfiller.backfill_household(h.id)
    # Both runs see 1 ingredient as matched (first run does the work,
    # second run finds it already resolved and reports "matched" = True
    # because the catalog ref is present).
    assert first.total_ingredients_matched == 1
    assert second.total_ingredients_matched == 1
    assert second.total_ingredients_skipped == 0


def test_backfill_preserves_original_ingredient_name(tmp_path):
    """The user-typed ingredient name is kept after backfill — only the
    catalog reference and servings count are added. Catalog `display_name`
    must NOT overwrite the original (the user wrote 'Skinless chicken
    thighs (~4 thighs)' and shouldn't see it morph into 'Chicken Breast'
    after a backfill)."""
    households, users, catalog, recipes, backfiller = _setup(tmp_path)
    h = households.create("Smiths")
    alice = users.create_user("Alice", "a@example.com", household_id=h.id, is_planner=True)

    # Phrasing matters: the sample DB has "Chicken Breast" (singular)
    # so we use a query that the matcher will resolve, while keeping the
    # original phrasing distinct from the catalog display name.
    original_name = "Skinless chicken breast (cubed)"
    recipes.save(Recipe(
        name="Test bowl",
        ingredients=[Ingredient(name=original_name, quantity=Decimal("6"), unit="oz")],
        base_servings=1,
        calories_per_serving=0,
    ), household_id=h.id, created_by_user_id=alice.user_id)

    backfiller.backfill_household(h.id)
    reloaded = recipes.find_all_by_household(h.id)[0]
    assert reloaded.ingredients[0].name == original_name
    # And the catalog link should still be made.
    assert reloaded.ingredients[0].catalog_ingredient_id is not None


def test_unmatched_ingredient_left_as_legacy(tmp_path):
    households, users, catalog, recipes, backfiller = _setup(tmp_path)
    h = households.create("Smiths")
    alice = users.create_user("Alice", "a@example.com", household_id=h.id, is_planner=True)

    recipes.save(Recipe(
        name="Mystery",
        ingredients=[Ingredient(name="flux capacitor dust", quantity=Decimal("1"), unit="cup")],
        base_servings=1,
        calories_per_serving=400,  # legacy fallback figure stays
    ), household_id=h.id, created_by_user_id=alice.user_id)

    report = backfiller.backfill_household(h.id)
    assert report.total_ingredients_matched == 0
    assert report.total_ingredients_skipped == 1
    skipped = report.recipe_results[0].ingredient_results[0]
    assert skipped.skip_reason == "no match in food database"

    # Recipe should be unchanged (still legacy).
    reloaded = recipes.find_all_by_household(h.id)[0]
    assert reloaded.calories_per_serving == 400
    assert reloaded.ingredients[0].catalog_ingredient_id is None
