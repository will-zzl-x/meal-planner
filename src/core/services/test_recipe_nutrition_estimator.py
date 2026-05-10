"""Tests for RecipeNutritionEstimator."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import Ingredient, Recipe
from core.services.food_database_service import FoodDatabaseService
from core.services.recipe_nutrition_estimator import (
    RecipeNutritionEstimator,
    _candidate_queries,
    _strip_parentheticals,
)


@pytest.fixture
def estimator() -> RecipeNutritionEstimator:
    # network_enabled=False keeps tests offline (sample DB only) so they're
    # deterministic and fast.
    return RecipeNutritionEstimator(FoodDatabaseService(network_enabled=False))


def _recipe(*ingredients: Ingredient, base_servings: int = 1) -> Recipe:
    return Recipe(
        name="Test recipe",
        ingredients=list(ingredients),
        base_servings=base_servings,
        calories_per_serving=0,
    )


def test_simple_oz_chicken_breast_estimate(estimator):
    # 6 oz chicken breast at 165 cal/100g = 165 * (6 * 28.35 / 100) ~= 281 cal
    recipe = _recipe(Ingredient("chicken breast", Decimal("6"), "oz"))
    estimate = estimator.estimate(recipe)
    assert estimate.skipped_count == 0
    assert 250 <= estimate.total_calories <= 320
    assert estimate.estimates[0].matched_food.lower().startswith("chicken breast")


def test_per_piece_egg_estimate(estimator):
    # 4 large eggs at 78 cal/each = 312 cal total, 156 per serving.
    recipe = _recipe(Ingredient("egg", Decimal("4"), "eggs"), base_servings=2)
    estimate = estimator.estimate(recipe)
    assert estimate.total_calories == 312
    assert estimate.total_calories_per_serving == 156


def test_per_serving_division(estimator):
    recipe = _recipe(
        Ingredient("chicken breast", Decimal("12"), "oz"),
        base_servings=2,
    )
    estimate = estimator.estimate(recipe)
    assert estimate.total_calories_per_serving == estimate.total_calories // 2


def test_zero_quantity_to_taste_is_skipped(estimator):
    recipe = _recipe(Ingredient("salt to taste", Decimal("0"), "tsp"))
    estimate = estimator.estimate(recipe)
    assert estimate.total_calories == 0
    assert estimate.skipped_count == 1
    assert "zero quantity" in estimate.estimates[0].skip_reason


def test_unknown_ingredient_is_reported(estimator):
    recipe = _recipe(Ingredient("flux capacitor dust", Decimal("1"), "cup"))
    estimate = estimator.estimate(recipe)
    assert estimate.skipped_count == 1
    assert estimate.estimates[0].skip_reason == "no match in food database"


def test_unconvertible_unit_is_reported(estimator):
    # "shakes" isn't in the unit-to-grams table → can't convert.
    recipe = _recipe(Ingredient("garlic powder", Decimal("12"), "shakes"))
    estimate = estimator.estimate(recipe)
    assert estimate.skipped_count == 1
    assert "can't convert" in estimate.estimates[0].skip_reason


def test_multiple_ingredients_sum_correctly(estimator):
    recipe = _recipe(
        Ingredient("chicken breast", Decimal("6"), "oz"),
        Ingredient("white rice cooked", Decimal("1"), "cup"),
    )
    estimate = estimator.estimate(recipe)
    # ~280 (chicken) + ~312 (1 cup rice ~ 240g * 1.30 cal/g) ~= ~590
    assert 500 <= estimate.total_calories <= 700
    assert estimate.skipped_count == 0


def test_strip_parentheticals():
    assert _strip_parentheticals("Skinless chicken thighs (~4 thighs)") == "Skinless chicken thighs"
    assert _strip_parentheticals("Garlic, minced (3 cloves)") == "Garlic, minced"


def test_candidate_queries_progressively_simpler():
    queries = _candidate_queries("Skinless chicken thighs (boneless skinless)")
    # Should include the full string, the parenthetical-stripped form, and
    # eventually a qualifier-stripped tail like "chicken thighs".
    assert any("chicken thighs" in q.lower() for q in queries)
