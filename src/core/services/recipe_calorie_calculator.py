"""
RecipeCalorieCalculator — sums calories from a recipe's catalog-backed ingredients.

A recipe's total calories = sum across each ingredient of
    (servings × catalog_ingredient.calories_per_serving)
where `servings` is the number of the catalog item's "serving_label"
(e.g. "1 large egg", "100g") used in the recipe. Ingredients that are
not catalog-backed (legacy free-text rows from before slice 8b) do not
contribute and are reported back as `unaccounted_count` so the UI can
show an honest caveat.

Per-serving = total ÷ recipe.base_servings, rounded to int.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List

from core.domain.models import Recipe
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)


@dataclass
class IngredientCalorieLine:
    name: str
    servings: Decimal
    serving_label: str
    calories_per_serving: int
    line_calories: int


@dataclass
class RecipeCalorieBreakdown:
    total_calories: int
    calories_per_serving: int
    lines: List[IngredientCalorieLine]
    unaccounted_count: int  # Ingredients without a catalog ref (no nutrition).


class RecipeCalorieCalculator:
    def __init__(self, catalog_repo: SQLiteIngredientCatalogRepository):
        self.catalog_repo = catalog_repo

    def compute(self, recipe: Recipe) -> RecipeCalorieBreakdown:
        # Recipe.__post_init__ already enforces base_servings >= 1.
        lines: List[IngredientCalorieLine] = []
        unaccounted = 0
        total = 0

        for ingredient in recipe.ingredients:
            if not ingredient.catalog_ingredient_id or ingredient.servings is None:
                unaccounted += 1
                continue

            catalog = self.catalog_repo.find_by_id(ingredient.catalog_ingredient_id)
            if catalog is None:
                # Catalog row was deleted under our feet — count as unaccounted
                # rather than crash. The UI can prompt the user to re-pick it.
                unaccounted += 1
                continue

            line_cal = int(round(float(ingredient.servings) * catalog.calories_per_serving))
            total += line_cal
            # Display the user's typed name (preserved by migration 010 via
            # recipe_ingredients.display_name) rather than the catalog's
            # canonical name. The catalog still drives the math; only the
            # label shown on screen comes from what the user wrote.
            lines.append(IngredientCalorieLine(
                name=ingredient.name,
                servings=ingredient.servings,
                serving_label=catalog.serving_label,
                calories_per_serving=catalog.calories_per_serving,
                line_calories=line_cal,
            ))

        per_serving = int(round(total / recipe.base_servings))
        return RecipeCalorieBreakdown(
            total_calories=total,
            calories_per_serving=per_serving,
            lines=lines,
            unaccounted_count=unaccounted,
        )
