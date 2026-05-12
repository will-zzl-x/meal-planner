"""Tests for RecipeScaler — ensures scaling preserves catalog references
on picker-backed recipes (regression from slice 8b).
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import Ingredient, Recipe
from core.services.recipe_scaler import RecipeScaler


def _picker_recipe() -> Recipe:
    return Recipe(
        name="Bowl",
        ingredients=[
            Ingredient(
                name="chicken breast",
                quantity=Decimal("2"),
                unit="100g",
                store="Costco",
                catalog_ingredient_id="cat-1",
                servings=Decimal("2"),
            ),
            Ingredient(
                name="rice",
                quantity=Decimal("1"),
                unit="100g",
                catalog_ingredient_id="cat-2",
                servings=Decimal("1"),
            ),
        ],
        base_servings=2,
        calories_per_serving=300,
    )


def test_scale_preserves_catalog_ingredient_id():
    scaler = RecipeScaler()
    scaled = scaler.scale_recipe_ingredients(_picker_recipe(), Decimal("2"))
    assert scaled[0].catalog_ingredient_id == "cat-1"
    assert scaled[1].catalog_ingredient_id == "cat-2"


def test_scale_doubles_servings():
    scaler = RecipeScaler()
    scaled = scaler.scale_recipe_ingredients(_picker_recipe(), Decimal("2"))
    assert scaled[0].servings == Decimal("4")
    assert scaled[1].servings == Decimal("2")


def test_scale_preserves_store_routing():
    scaler = RecipeScaler()
    scaled = scaler.scale_recipe_ingredients(_picker_recipe(), Decimal("0.5"))
    assert scaled[0].store == "Costco"
    assert scaled[1].store is None


def test_scale_legacy_ingredient_servings_stays_none():
    """Legacy free-text ingredients have no `servings`; scaling must
    leave that None rather than crashing or fabricating one."""
    legacy = Recipe(
        name="Legacy",
        ingredients=[Ingredient(name="butter", quantity=Decimal("4"), unit="tbsp")],
        base_servings=2, calories_per_serving=100,
    )
    scaler = RecipeScaler()
    scaled = scaler.scale_recipe_ingredients(legacy, Decimal("2"))
    assert scaled[0].servings is None
    assert scaled[0].catalog_ingredient_id is None
