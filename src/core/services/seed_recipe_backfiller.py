"""
Best-effort backfill of legacy / seed recipe ingredients into catalog-backed
ingredients with real per-serving nutrition.

Strategy per ingredient:
1. If the ingredient already has a `catalog_ingredient_id` — leave it alone
   (idempotent). Re-runs only touch unresolved ingredients.
2. Search FoodDatabaseService for the ingredient name with progressively
   simpler queries (parentheticals stripped, qualifier words dropped).
3. Take the top match.
4. Convert the recipe's `(quantity, unit)` into "servings of the catalog
   item's serving label" using a unit-conversion table. If the catalog
   item is per-piece, the recipe must use a piece-style unit.
5. Persist the catalog row, update the recipe's ingredient with the
   catalog ref + servings count.
6. After all ingredients are processed, recompute the recipe's stored
   `calories_per_serving` from its now-catalog-backed lines.

Anything that can't be auto-matched is left untouched and reported back so
the user knows to fix it via the picker.

Honest limitations:
- The unit "cup" is approximated as 240 g for any ingredient. That's
  accurate for water-density things and badly off for dense dry goods.
  V1 acceptable; future improvement is per-ingredient density.
- "Hot honey" or other niche items may not match well; we accept that.
- The match is best-effort; the planner still has the picker to fix
  individual lines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from core.domain.models import CatalogIngredient, FoodItem, Ingredient, Recipe
from core.services.food_database_service import FoodDatabaseService
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository


# Approximate grams per unit. "cup" is the messiest — kept at the water-
# density value of 240 g. See module docstring.
_UNIT_TO_GRAMS = {
    "g": Decimal("1"),
    "gram": Decimal("1"),
    "grams": Decimal("1"),
    "kg": Decimal("1000"),
    "oz": Decimal("28.35"),
    "ounce": Decimal("28.35"),
    "ounces": Decimal("28.35"),
    "lb": Decimal("453.59"),
    "lbs": Decimal("453.59"),
    "pound": Decimal("453.59"),
    "pounds": Decimal("453.59"),
    "cup": Decimal("240"),
    "cups": Decimal("240"),
    "tbsp": Decimal("15"),
    "tablespoon": Decimal("15"),
    "tablespoons": Decimal("15"),
    "tsp": Decimal("5"),
    "teaspoon": Decimal("5"),
    "teaspoons": Decimal("5"),
    "ml": Decimal("1"),       # treat ml ≈ g for cooking purposes
}

# Recipe units that mean "discrete pieces" — when the catalog item is
# per-piece, the recipe quantity is the count.
_PIECE_UNITS = {
    "piece", "pieces", "whole", "egg", "eggs",
    "thigh", "thighs", "breast", "breasts",
    "lemon", "lemons", "lime", "limes", "tomato", "tomatoes",
    "onion", "onions", "pepper", "peppers", "potato", "potatoes",
    "stalk", "stalks", "rib", "ribs", "clove", "cloves",
    "sprig", "sprigs", "bulb", "bulbs",
    "bun", "buns", "head", "heads", "slice", "slices",
    "steak", "steaks", "fillet", "fillets",
    "packet", "packets", "pack", "packs",
    "bunch", "bunches", "handful", "handfuls", "tray", "trays",
    "bag", "bags", "can", "cans", "shake", "shakes", "large", "medium", "small",
}

# Words to strip when building progressively simpler search queries.
_QUALIFIERS = {
    "raw", "fresh", "cooked", "diced", "minced", "chopped", "sliced",
    "julienned", "halved", "cubed", "torn", "trimmed", "skinless", "boneless",
    "ground", "shredded", "grated", "thinly", "small", "medium", "large",
    "frozen", "canned", "dry", "dried", "boiled", "steamed", "roasted",
    "to", "taste",
}


@dataclass
class IngredientResolution:
    ingredient_name: str
    matched: bool
    catalog_id: Optional[str] = None
    catalog_name: Optional[str] = None
    servings: Optional[Decimal] = None
    skip_reason: Optional[str] = None  # When matched=False.


@dataclass
class RecipeResolution:
    recipe_id: str
    recipe_name: str
    ingredient_results: List[IngredientResolution] = field(default_factory=list)
    new_calories_per_serving: Optional[int] = None  # None if no ingredients matched

    @property
    def matched_count(self) -> int:
        return sum(1 for ir in self.ingredient_results if ir.matched)

    @property
    def skipped_count(self) -> int:
        return sum(1 for ir in self.ingredient_results if not ir.matched)


@dataclass
class BackfillReport:
    recipe_results: List[RecipeResolution] = field(default_factory=list)

    @property
    def total_recipes(self) -> int:
        return len(self.recipe_results)

    @property
    def total_ingredients_matched(self) -> int:
        return sum(r.matched_count for r in self.recipe_results)

    @property
    def total_ingredients_skipped(self) -> int:
        return sum(r.skipped_count for r in self.recipe_results)


class SeedRecipeBackfiller:
    def __init__(self,
                 food_db: FoodDatabaseService,
                 catalog_repo: SQLiteIngredientCatalogRepository,
                 recipe_repo: SQLiteRecipeRepository):
        self.food_db = food_db
        self.catalog_repo = catalog_repo
        self.recipe_repo = recipe_repo

    def backfill_household(self, household_id: str) -> BackfillReport:
        """Resolve every still-unresolved ingredient across the household's
        recipes. Idempotent — already-resolved ingredients are skipped."""
        report = BackfillReport()
        recipes = self.recipe_repo.find_all_by_household(household_id)
        for recipe in recipes:
            report.recipe_results.append(self._backfill_recipe(recipe, household_id))
        return report

    def _backfill_recipe(self, recipe: Recipe, household_id: str) -> RecipeResolution:
        result = RecipeResolution(
            recipe_id=recipe.id or "",
            recipe_name=recipe.name,
        )

        new_ingredients: List[Ingredient] = []
        any_changed = False

        for ingredient in recipe.ingredients:
            if ingredient.catalog_ingredient_id and ingredient.servings is not None:
                # Already resolved; carry forward unchanged.
                new_ingredients.append(ingredient)
                result.ingredient_results.append(IngredientResolution(
                    ingredient_name=ingredient.name,
                    matched=True,
                    catalog_id=ingredient.catalog_ingredient_id,
                    catalog_name=ingredient.name,
                    servings=ingredient.servings,
                ))
                continue

            resolution, resolved_ingredient = self._resolve(ingredient)
            result.ingredient_results.append(resolution)
            if resolved_ingredient is not None:
                new_ingredients.append(resolved_ingredient)
                any_changed = True
            else:
                # Couldn't match — keep the legacy free-text row.
                new_ingredients.append(ingredient)

        if not any_changed:
            return result  # nothing to write

        # Recompute the stored calories_per_serving from the resolved lines.
        total_cal = 0
        for ing in new_ingredients:
            if ing.catalog_ingredient_id and ing.servings is not None:
                catalog = self.catalog_repo.find_by_id(ing.catalog_ingredient_id)
                if catalog:
                    total_cal += int(round(float(ing.servings) * catalog.calories_per_serving))
        recipe.ingredients = new_ingredients
        recipe.calories_per_serving = (
            int(round(total_cal / recipe.base_servings))
            if recipe.base_servings > 0 else 0
        )
        result.new_calories_per_serving = recipe.calories_per_serving
        self.recipe_repo.update(recipe, household_id=household_id)
        return result

    def _resolve(self, ingredient: Ingredient) -> tuple[IngredientResolution, Optional[Ingredient]]:
        """Try to find a catalog item for `ingredient` and return a resolved
        Ingredient. Returns (resolution_report, resolved_ingredient_or_None)."""
        if ingredient.quantity <= 0:
            return (IngredientResolution(
                ingredient_name=ingredient.name,
                matched=False,
                skip_reason="zero quantity (to taste / placeholder)",
            ), None)

        food_match = self._find_food_match(ingredient.name)
        if food_match is None:
            return (IngredientResolution(
                ingredient_name=ingredient.name,
                matched=False,
                skip_reason="no match in food database",
            ), None)

        servings = _convert_to_servings(
            quantity=ingredient.quantity,
            recipe_unit=ingredient.unit,
            catalog_serving_label=food_match.unit,
        )
        if servings is None:
            return (IngredientResolution(
                ingredient_name=ingredient.name,
                matched=False,
                skip_reason=(
                    f"can't convert '{ingredient.unit}' to "
                    f"'{food_match.unit}' for {food_match.name}"
                ),
            ), None)

        # Persist the catalog row (idempotent on source+external_id).
        catalog = self.catalog_repo.save(CatalogIngredient.from_food_item(food_match))

        # Preserve the *original* ingredient name (e.g. the seed text
        # "Skinless chicken thighs (~4 thighs)") rather than overwriting
        # with the catalog's display name. The user wrote that name and
        # may not recognize "Chicken Breast" as the same thing on the
        # recipe card. The link is still made via catalog_ingredient_id.
        resolved = Ingredient(
            name=ingredient.name,
            quantity=servings,                # legacy field — store servings count here
            unit=catalog.serving_label,       # legacy field — store catalog serving label
            store=ingredient.store,           # preserve store routing
            catalog_ingredient_id=catalog.id,
            servings=servings,
        )

        return (IngredientResolution(
            ingredient_name=ingredient.name,
            matched=True,
            catalog_id=catalog.id,
            catalog_name=catalog.display_name,
            servings=servings,
        ), resolved)

    def _find_food_match(self, ingredient_name: str) -> Optional[FoodItem]:
        for query in _candidate_queries(ingredient_name):
            results = self.food_db.search_food_database(query, limit=8)
            if results:
                return results[0]
        return None


# ------------------------------------------------- helpers (pure functions)

def _convert_to_servings(*,
                         quantity: Decimal,
                         recipe_unit: str,
                         catalog_serving_label: str) -> Optional[Decimal]:
    """Convert (qty, recipe_unit) to (servings of catalog_serving_label).

    Two cases:
    - catalog item is per-piece ("piece", "1 large egg", etc.):
      recipe_unit must be a piece-style word; servings = qty.
    - catalog item is per-100g (or "100g"): recipe_unit must be in
      _UNIT_TO_GRAMS; servings = qty * grams_per_unit / 100.
    """
    catalog_unit = (catalog_serving_label or "").strip().lower()
    recipe_unit = (recipe_unit or "").strip().lower()

    is_piece = "piece" in catalog_unit or _looks_per_piece(catalog_unit)
    if is_piece:
        if recipe_unit in _PIECE_UNITS or recipe_unit == "":
            return quantity
        # Catalog says per-piece, recipe says oz/cup/etc — can't convert.
        return None

    # Catalog is mass-based. Need to convert recipe units to grams.
    if catalog_unit in ("100g", "100 g", "100ml", "100 ml"):
        grams_per_unit = _UNIT_TO_GRAMS.get(recipe_unit)
        if grams_per_unit is None:
            return None
        total_grams = quantity * grams_per_unit
        return total_grams / Decimal("100")

    # Anything else (e.g. catalog reports "227 g" or "1 cup (240 g)") —
    # try to extract grams from the label.
    grams = _extract_grams_from_label(catalog_unit)
    if grams is not None and grams > 0:
        grams_per_unit = _UNIT_TO_GRAMS.get(recipe_unit)
        if grams_per_unit is None:
            return None
        total_grams = quantity * grams_per_unit
        return total_grams / Decimal(str(grams))

    return None


def _looks_per_piece(label: str) -> bool:
    """Heuristic: catalog labels like '1 large egg', '1 bun' are per-piece.
    A weight or volume token anywhere in the label means it isn't."""
    if _extract_grams_from_label(label) is not None:
        return False  # has a gram value somewhere — mass-based.
    tokens = label.split()
    if not tokens:
        return False
    return tokens[0] in ("1",)


def _extract_grams_from_label(label: str) -> Optional[Decimal]:
    """Pull a gram value out of labels like '1 cup (227 g)' or '227 g'."""
    import re
    match = re.search(r"(\d+(?:\.\d+)?)\s*g\b", label)
    if match:
        try:
            return Decimal(match.group(1))
        except Exception:
            return None
    return None


def _candidate_queries(ingredient_name: str) -> List[str]:
    """Yield progressively simpler search queries for an ingredient name."""
    base = ingredient_name.strip()
    queries: List[str] = []

    def _add(q: str) -> None:
        q = q.strip()
        if q and q not in queries:
            queries.append(q)

    _add(base)
    cleaned = _strip_parentheticals(base)
    _add(cleaned)
    if "," in cleaned:
        _add(cleaned.split(",", 1)[0])
    tokens = [t for t in cleaned.lower().split() if t not in _QUALIFIERS]
    if tokens:
        _add(" ".join(tokens))
    head = " ".join(cleaned.split()[:2])
    _add(head)
    return queries


def _strip_parentheticals(s: str) -> str:
    out, depth = [], 0
    for ch in s:
        if ch == "(":
            depth += 1
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            out.append(ch)
    return "".join(out).strip()
