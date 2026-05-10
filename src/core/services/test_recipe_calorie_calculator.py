"""Tests for RecipeCalorieCalculator (slice 8b)."""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import CatalogIngredient, Ingredient, Recipe
from core.services.recipe_calorie_calculator import RecipeCalorieCalculator
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)


def _setup(tmp_path):
    catalog = SQLiteIngredientCatalogRepository(str(tmp_path / "test.db"))
    calc = RecipeCalorieCalculator(catalog)
    return catalog, calc


def _seed_catalog(catalog: SQLiteIngredientCatalogRepository,
                  name: str, cal_per_serving: int, label: str = "100g",
                  external_id: str = "x") -> str:
    saved = catalog.save(CatalogIngredient(
        id="",
        name=name,
        serving_label=label,
        calories_per_serving=cal_per_serving,
        source="usda",
        external_id=external_id,
    ))
    return saved.id


def test_sums_catalog_backed_ingredients(tmp_path):
    catalog, calc = _setup(tmp_path)
    chicken_id = _seed_catalog(catalog, "Chicken Breast", cal_per_serving=165, external_id="c1")
    rice_id = _seed_catalog(catalog, "White Rice", cal_per_serving=130, external_id="r1")

    # 1.5 servings of chicken (1.5 * 165 = 247.5 → 248) + 2 servings of rice (260) = 508
    recipe = Recipe(
        name="Chicken bowl",
        ingredients=[
            Ingredient(name="Chicken Breast", quantity=Decimal("1.5"), unit="100g",
                       catalog_ingredient_id=chicken_id, servings=Decimal("1.5")),
            Ingredient(name="White Rice", quantity=Decimal("2"), unit="100g",
                       catalog_ingredient_id=rice_id, servings=Decimal("2")),
        ],
        base_servings=2,
        calories_per_serving=0,
    )
    result = calc.compute(recipe)
    assert result.total_calories == 248 + 260
    assert result.calories_per_serving == result.total_calories // 2
    assert result.unaccounted_count == 0
    assert len(result.lines) == 2


def test_legacy_free_text_ingredients_are_unaccounted(tmp_path):
    catalog, calc = _setup(tmp_path)
    chicken_id = _seed_catalog(catalog, "Chicken Breast", 165, external_id="c1")

    recipe = Recipe(
        name="Mixed",
        ingredients=[
            Ingredient(name="Chicken Breast", quantity=Decimal("1"), unit="100g",
                       catalog_ingredient_id=chicken_id, servings=Decimal("1")),
            Ingredient(name="Some legacy thing", quantity=Decimal("3"), unit="oz"),
        ],
        base_servings=1,
        calories_per_serving=0,
    )
    result = calc.compute(recipe)
    assert result.total_calories == 165
    assert result.unaccounted_count == 1


def test_missing_catalog_row_treated_as_unaccounted(tmp_path):
    """If a catalog row is deleted under us, the recipe doesn't crash."""
    _, calc = _setup(tmp_path)
    recipe = Recipe(
        name="Stale",
        ingredients=[
            Ingredient(name="Ghost", quantity=Decimal("1"), unit="100g",
                       catalog_ingredient_id="does-not-exist", servings=Decimal("1")),
        ],
        base_servings=1,
        calories_per_serving=0,
    )
    result = calc.compute(recipe)
    assert result.total_calories == 0
    assert result.unaccounted_count == 1


def test_line_uses_ingredient_name_not_catalog_display_name(tmp_path):
    """The calorie line shown to the user should carry the *ingredient*'s
    name (the user-typed phrasing preserved on each recipe row), not the
    catalog row's canonical name. This avoids a recipe whose seed text
    said 'Skinless chicken thighs (~4)' visibly morphing into 'Chicken
    Breast' once it's matched to a catalog row."""
    catalog, calc = _setup(tmp_path)
    cid = _seed_catalog(catalog, "Chicken Breast", 165, external_id="c1")

    recipe = Recipe(
        name="Bowl",
        ingredients=[
            Ingredient(
                name="Skinless chicken breasts (~4)",
                quantity=Decimal("1"),
                unit="100g",
                catalog_ingredient_id=cid,
                servings=Decimal("1"),
            ),
        ],
        base_servings=1,
        calories_per_serving=0,
    )
    result = calc.compute(recipe)
    assert len(result.lines) == 1
    assert result.lines[0].name == "Skinless chicken breasts (~4)"
    # And the math is still driven by the catalog's per-serving value.
    assert result.lines[0].calories_per_serving == 165


def test_per_serving_division(tmp_path):
    catalog, calc = _setup(tmp_path)
    cid = _seed_catalog(catalog, "Cake", 1000)
    recipe = Recipe(
        name="Cake recipe",
        ingredients=[
            Ingredient(name="Cake", quantity=Decimal("4"), unit="100g",
                       catalog_ingredient_id=cid, servings=Decimal("4")),
        ],
        base_servings=8,
        calories_per_serving=0,
    )
    result = calc.compute(recipe)
    assert result.total_calories == 4000
    assert result.calories_per_serving == 500


