"""
Slim grocery-list service for V1.

Takes a household's meal plan entries plus its current pantry and returns the
list of ingredients that still need to be bought, deduped by (name, unit).

This deliberately doesn't use the calorie-banking-aware
EnhancedGroceryListGenerator — that flow is geared at re-balancing macros
across a week. V1's grocery list is a straight subtract: planned needs
minus pantry on hand.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

from core.domain.models import GroceryListItem, InventoryItem, Recipe
from core.interfaces.meal_plan_repository import MealPlanEntry


class GroceryListService:
    """Aggregate plan entries to a shopping list, subtracting pantry on hand."""

    def generate(self,
                 entries: List[MealPlanEntry],
                 recipes_by_id: Dict[str, Recipe],
                 pantry: List[InventoryItem]) -> List[GroceryListItem]:
        needed: Dict[Tuple[str, str], Decimal] = {}

        for entry in entries:
            recipe = recipes_by_id.get(entry.recipe_id)
            if recipe is None or recipe.base_servings <= 0:
                continue
            scale = Decimal(entry.planned_servings) / Decimal(recipe.base_servings)
            for ing in recipe.ingredients:
                key = (ing.name, ing.unit)
                needed[key] = needed.get(key, Decimal("0")) + (ing.quantity * scale)

        for item in pantry:
            key = (item.name, item.unit)
            if key not in needed:
                continue
            needed[key] -= item.quantity

        return [
            GroceryListItem(
                name=name,
                display_amount=_format_quantity(qty),
                actual_need=_format_quantity(qty),
                unit=unit,
            )
            for (name, unit), qty in sorted(needed.items())
            if qty > 0
        ]


def _format_quantity(qty: Decimal) -> str:
    """Render a Decimal without trailing zeros (e.g. '2' not '2.00')."""
    normalized = qty.normalize()
    # normalize() can produce scientific notation for whole numbers; force plain.
    return f"{normalized:f}" if normalized == normalized.to_integral_value() else str(normalized)
