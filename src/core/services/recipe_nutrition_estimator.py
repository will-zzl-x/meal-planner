"""
RecipeNutritionEstimator — best-effort calories per serving from a recipe.

The estimator pairs each ingredient with the closest match from
FoodDatabaseService and converts the ingredient's quantity to grams or to
discrete pieces, depending on which "unit base" the food item reports.
Everything it can't match (rare ingredients, non-convertible units like
"shakes" or "handful") is reported back so the caller can show the user
what was skipped.

Limitations to be honest about:
- "1 cup" is approximated as 240 g for any ingredient. That's accurate for
  water-density things like yogurt or broth and badly off for dry rice or
  oats. Acceptable for V1 ballpark estimates; future improvement is per-
  ingredient density.
- The match is by lowercase substring — first hit wins.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from core.domain.models import Ingredient, Recipe
from core.services.food_database_service import FoodDatabaseService, FoodItem


# Approximate grams per unit. "cup" is the messiest — kept at the water-
# density value of 240 g and called out in the docstring.
_UNIT_TO_GRAMS = {
    "g": Decimal("1"),
    "kg": Decimal("1000"),
    "oz": Decimal("28.35"),
    "lb": Decimal("453.59"),
    "cup": Decimal("240"),
    "tbsp": Decimal("15"),
    "tsp": Decimal("5"),
}

# Units the estimator treats as "discrete pieces" — multiply ingredient
# quantity directly by the food's per-piece calorie figure.
_PIECE_UNITS = {
    "piece", "pieces", "whole", "egg", "eggs",
    "thigh", "thighs", "breast", "breasts",
    "lemon", "lime", "tomato", "tomatoes",
    "onion", "pepper", "peppers", "potato",
    "stalk", "stalks", "rib", "ribs", "clove", "cloves",
    "sprig", "sprigs", "bulb", "bulbs",
    "bun", "buns", "head", "heads", "slice", "slices",
}


@dataclass
class IngredientEstimate:
    """One ingredient's contribution to the recipe total."""
    ingredient_name: str
    estimated_calories: Optional[int]  # None if not estimable.
    matched_food: Optional[str] = None
    skip_reason: Optional[str] = None  # "no match" / "unknown unit" / "zero quantity".


@dataclass
class NutritionEstimate:
    """Complete estimator output. `total_calories_per_serving` is rounded."""
    total_calories: int
    total_calories_per_serving: int
    estimates: List[IngredientEstimate]
    skipped_count: int


class RecipeNutritionEstimator:
    def __init__(self, food_db: FoodDatabaseService):
        self.food_db = food_db

    def estimate(self, recipe: Recipe) -> NutritionEstimate:
        if recipe.base_servings <= 0:
            raise ValueError("Recipe.base_servings must be >= 1")

        estimates: List[IngredientEstimate] = []
        total = Decimal("0")
        skipped = 0

        for ingredient in recipe.ingredients:
            estimate = self._estimate_ingredient(ingredient)
            estimates.append(estimate)
            if estimate.estimated_calories is None:
                skipped += 1
            else:
                total += Decimal(estimate.estimated_calories)

        total_int = int(total)
        per_serving = int(total // recipe.base_servings)
        return NutritionEstimate(
            total_calories=total_int,
            total_calories_per_serving=per_serving,
            estimates=estimates,
            skipped_count=skipped,
        )

    def _estimate_ingredient(self, ingredient: Ingredient) -> IngredientEstimate:
        # "to taste" entries use quantity 0 — surface them rather than silently
        # contributing nothing.
        if ingredient.quantity <= 0:
            return IngredientEstimate(
                ingredient_name=ingredient.name,
                estimated_calories=None,
                skip_reason="zero quantity (to taste / placeholder)",
            )

        food_match = self._find_food_match(ingredient.name)
        if food_match is None:
            return IngredientEstimate(
                ingredient_name=ingredient.name,
                estimated_calories=None,
                skip_reason="no match in food database",
            )

        calories = self._calories_for(ingredient, food_match)
        if calories is None:
            return IngredientEstimate(
                ingredient_name=ingredient.name,
                estimated_calories=None,
                matched_food=food_match.name,
                skip_reason=f"can't convert unit '{ingredient.unit}' for {food_match.name}",
            )
        return IngredientEstimate(
            ingredient_name=ingredient.name,
            estimated_calories=calories,
            matched_food=food_match.name,
        )

    def _find_food_match(self, ingredient_name: str) -> Optional[FoodItem]:
        """Search the food database for the ingredient. Tries the full name,
        then the simplified core (parentheticals stripped, common qualifiers
        removed)."""
        # Note: food_db.search_food_database halves `limit` between sample and
        # API results, so we ask for at least 4 to ensure non-empty matches.
        for query in _candidate_queries(ingredient_name):
            results = self.food_db.search_food_database(query, limit=8)
            if results:
                return results[0]
        return None

    def _calories_for(self, ingredient: Ingredient, food: FoodItem) -> Optional[int]:
        unit = (ingredient.unit or "").lower().strip()
        food_unit = (food.unit or "").lower().strip()

        # Per-piece food (egg, lemon, bell pepper) — ingredient quantity is the count.
        if food_unit == "piece":
            if unit in _PIECE_UNITS or unit == "":
                return int(Decimal(food.calories_per_unit) * ingredient.quantity)
            # Falls through to gram-based path below for awkward cases (e.g.
            # food item "Avocado" reports per-piece, ingredient asks for oz).
            return None

        # Per-100g food. Convert ingredient quantity → grams, scale.
        if food_unit == "100g":
            grams = _UNIT_TO_GRAMS.get(unit)
            if grams is None:
                return None
            total_grams = ingredient.quantity * grams
            return int(Decimal(food.calories_per_unit) * total_grams / Decimal("100"))

        return None


# A handful of cooking qualifiers we strip while building search queries.
_QUALIFIERS = {
    "raw", "fresh", "cooked", "diced", "minced", "chopped", "sliced",
    "julienned", "halved", "cubed", "torn", "trimmed", "skinless", "boneless",
    "ground", "shredded", "grated", "thinly", "small", "medium", "large",
    "frozen", "canned",
}


def _candidate_queries(ingredient_name: str) -> List[str]:
    """Yield progressively simpler search queries for an ingredient name."""
    base = ingredient_name.strip()
    queries: List[str] = []

    def _add(q: str) -> None:
        q = q.strip()
        if q and q not in queries:
            queries.append(q)

    _add(base)

    # Drop parenthetical content: "Skinless chicken thighs (~4 thighs)" → "Skinless chicken thighs"
    cleaned = _strip_parentheticals(base)
    _add(cleaned)

    # Drop trailing comma-prefixed qualifiers ("Garlic, minced" → "Garlic")
    if "," in cleaned:
        _add(cleaned.split(",", 1)[0])

    # Strip qualifier words ("Skinless chicken thighs" → "chicken thighs").
    tokens = [t for t in cleaned.lower().split() if t not in _QUALIFIERS]
    if tokens:
        _add(" ".join(tokens))

    # Last resort: first two words.
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
