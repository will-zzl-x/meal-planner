"""
RecipeCalorieCalculator — sums calories and macros from a recipe's
catalog-backed ingredients.

A recipe's total calories = sum across each ingredient of
    (servings × catalog_ingredient.calories_per_serving)
where `servings` is the number of the catalog item's "serving_label"
(e.g. "1 large egg", "100g") used in the recipe. Protein/carbs/fat
follow the same shape. Ingredients that are not catalog-backed (legacy
free-text rows from before slice 8b) do not contribute and are reported
back as `unaccounted_count` so the UI can show an honest caveat.

Per-serving = total ÷ recipe.base_servings, rounded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    # Macros — populated alongside calories from the same catalog rows.
    total_protein: Decimal = field(default_factory=lambda: Decimal("0"))
    total_carbs: Decimal = field(default_factory=lambda: Decimal("0"))
    total_fat: Decimal = field(default_factory=lambda: Decimal("0"))
    protein_per_serving: Decimal = field(default_factory=lambda: Decimal("0"))
    carbs_per_serving: Decimal = field(default_factory=lambda: Decimal("0"))
    fat_per_serving: Decimal = field(default_factory=lambda: Decimal("0"))


class RecipeCalorieCalculator:
    def __init__(self, catalog_repo: SQLiteIngredientCatalogRepository):
        self.catalog_repo = catalog_repo

    def compute(self, recipe: Recipe) -> RecipeCalorieBreakdown:
        # Recipe.__post_init__ already enforces base_servings >= 1.
        lines: List[IngredientCalorieLine] = []
        unaccounted = 0
        total = 0
        total_p = Decimal("0")
        total_c = Decimal("0")
        total_f = Decimal("0")

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

            servings = ingredient.servings
            line_cal = int(round(float(servings) * catalog.calories_per_serving))
            total += line_cal
            total_p += servings * catalog.protein_per_serving
            total_c += servings * catalog.carbs_per_serving
            total_f += servings * catalog.fat_per_serving
            # Display the user's typed name (preserved by migration 010 via
            # recipe_ingredients.display_name) rather than the catalog's
            # canonical name. The catalog still drives the math; only the
            # label shown on screen comes from what the user wrote.
            lines.append(IngredientCalorieLine(
                name=ingredient.name,
                servings=servings,
                serving_label=catalog.serving_label,
                calories_per_serving=catalog.calories_per_serving,
                line_calories=line_cal,
            ))

        servings_div = Decimal(recipe.base_servings)
        per_serving = int(round(total / recipe.base_servings))
        return RecipeCalorieBreakdown(
            total_calories=total,
            calories_per_serving=per_serving,
            lines=lines,
            unaccounted_count=unaccounted,
            total_protein=total_p,
            total_carbs=total_c,
            total_fat=total_f,
            protein_per_serving=total_p / servings_div,
            carbs_per_serving=total_c / servings_div,
            fat_per_serving=total_f / servings_div,
        )
