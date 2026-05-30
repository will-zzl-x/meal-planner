"""Tests for CycleMacroService."""
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import CatalogIngredient, Ingredient, Recipe
from core.interfaces.meal_plan_repository import MealPlanEntry
from core.services.cycle_macro_service import CycleMacroService
from core.services.recipe_calorie_calculator import RecipeCalorieCalculator
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)


def _setup(tmp_path):
    catalog = SQLiteIngredientCatalogRepository(str(tmp_path / "test.db"))
    calc = RecipeCalorieCalculator(catalog)
    svc = CycleMacroService(calc)
    return catalog, svc


def _seed(catalog, name, cal, protein, carbs, fat, ext_id):
    saved = catalog.save(CatalogIngredient(
        id="",
        name=name,
        serving_label="100g",
        calories_per_serving=cal,
        protein_per_serving=Decimal(str(protein)),
        carbs_per_serving=Decimal(str(carbs)),
        fat_per_serving=Decimal(str(fat)),
        source="usda",
        external_id=ext_id,
    ))
    return saved.id


def _entry(recipe_id, planned_date, servings=1, meal="dinner",
           recipe_name="x", cal_per_serving=0):
    return MealPlanEntry(
        id=f"e-{recipe_id}-{planned_date}-{meal}",
        recipe_id=recipe_id,
        planned_date=planned_date,
        planned_servings=servings,
        meal_type=meal,
        recipe_name=recipe_name,
        calories_per_serving=cal_per_serving,
    )


def test_empty_cycle_returns_zero_rows(tmp_path):
    _, svc = _setup(tmp_path)
    start = date(2026, 5, 21)
    end = start + timedelta(days=2)
    summary = svc.summarize(start, end, entries=[], recipes_by_id={})
    assert len(summary.days) == 3
    assert summary.total_calories == 0
    assert summary.total_protein == Decimal("0")
    assert not summary.has_any_unaccounted


def test_sums_per_day_from_catalog_recipes(tmp_path):
    catalog, svc = _setup(tmp_path)
    chicken_id = _seed(catalog, "Chicken", 165, 31, 0, 3.6, "c1")
    rice_id = _seed(catalog, "Rice", 130, 2.7, 28, 0.3, "r1")

    recipe = Recipe(
        name="Bowl",
        ingredients=[
            Ingredient("Chicken", Decimal("2"), "100g",
                       catalog_ingredient_id=chicken_id, servings=Decimal("2")),
            Ingredient("Rice", Decimal("2"), "100g",
                       catalog_ingredient_id=rice_id, servings=Decimal("2")),
        ],
        base_servings=2,
        calories_per_serving=0,
    )
    recipe.id = "r1"

    start = date(2026, 5, 21)
    end = start + timedelta(days=1)
    entries = [_entry("r1", start, servings=2, cal_per_serving=0)]

    summary = svc.summarize(start, end, entries, recipes_by_id={"r1": recipe})

    # per-serving from calculator: (330 + 260) / 2 = 295 cal/serving
    # 2 servings on day 1 → 590 cal
    assert summary.days[0].calories == 590
    # protein per serving = (62 + 5.4)/2 = 33.7; × 2 servings = 67.4
    assert summary.days[0].protein == Decimal("67.4")
    assert summary.days[1].calories == 0
    assert summary.total_calories == 590


def test_legacy_recipe_falls_back_to_stored_calories(tmp_path):
    catalog, svc = _setup(tmp_path)
    # No catalog ingredients — purely free-text recipe.
    legacy = Recipe(
        name="Legacy",
        ingredients=[Ingredient("noodles", Decimal("1"), "cup")],
        base_servings=1,
        calories_per_serving=400,
    )
    legacy.id = "legacy"

    start = date(2026, 5, 21)
    entries = [_entry("legacy", start, servings=2, cal_per_serving=400)]
    summary = svc.summarize(start, start, entries, recipes_by_id={"legacy": legacy})

    assert summary.days[0].calories == 800  # 2 × 400
    assert summary.days[0].protein == Decimal("0")
    assert summary.days[0].unaccounted_entries == 1
    assert summary.has_any_unaccounted


def test_entries_outside_window_are_ignored(tmp_path):
    _, svc = _setup(tmp_path)
    legacy = Recipe(
        name="X",
        ingredients=[Ingredient("noodles", Decimal("1"), "cup")],
        base_servings=1,
        calories_per_serving=100,
    )
    legacy.id = "x"
    start = date(2026, 5, 21)
    end = start + timedelta(days=2)
    entries = [
        _entry("x", start - timedelta(days=1), cal_per_serving=100),
        _entry("x", start, cal_per_serving=100),
        _entry("x", end + timedelta(days=1), cal_per_serving=100),
    ]
    summary = svc.summarize(start, end, entries, recipes_by_id={"x": legacy})
    assert summary.total_calories == 100
    assert summary.days[0].calories == 100
    assert summary.days[1].calories == 0
    assert summary.days[2].calories == 0


def test_missing_recipe_in_lookup_still_uses_stored_calories(tmp_path):
    _, svc = _setup(tmp_path)
    start = date(2026, 5, 21)
    entries = [_entry("ghost", start, servings=3, cal_per_serving=200)]
    summary = svc.summarize(start, start, entries, recipes_by_id={})
    assert summary.days[0].calories == 600
    assert summary.days[0].unaccounted_entries == 1
