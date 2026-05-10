"""
Slim grocery-list service for V1.

Takes a household's meal plan entries plus its current pantry and returns the
list of ingredients that still need to be bought.

After V2 the service uses TWO matching paths:

1. **Catalog-keyed**: when a recipe ingredient has a `catalog_ingredient_id`,
   we aggregate by that id and subtract any pantry rows that share the same
   id — converting pantry's free-text quantity into the recipe's catalog
   serving units (g, pieces, etc.) via `_convert_to_servings`. This is exact:
   "1 lb chicken" in the pantry correctly cancels "200g chicken" in the recipe.

2. **Legacy (name, unit)**: when either side lacks a catalog reference, we
   fall back to the original literal (name, unit) match. This keeps unedited
   seed recipes and free-text pantry rows working until they're migrated.

Both paths produce GroceryListItem rows; results are merged and sorted by
display name.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

from core.domain.models import GroceryListItem, InventoryItem, Recipe
from core.interfaces.meal_plan_repository import MealPlanEntry
from core.services.seed_recipe_backfiller import _convert_to_servings


class GroceryListService:
    """Aggregate plan entries to a shopping list, subtracting pantry on hand."""

    def generate(self,
                 entries: List[MealPlanEntry],
                 recipes_by_id: Dict[str, Recipe],
                 pantry: List[InventoryItem]) -> List[GroceryListItem]:
        # Two buckets — catalog-keyed (exact, with unit conversion) and
        # legacy (name+unit literal match).
        catalog_needed: Dict[str, Decimal] = {}
        # display_name + catalog serving_label keyed by catalog_id, taken
        # from the first recipe ingredient that references it.
        catalog_meta: Dict[str, Tuple[str, str]] = {}
        legacy_needed: Dict[Tuple[str, str], Decimal] = {}

        for entry in entries:
            recipe = recipes_by_id.get(entry.recipe_id)
            if recipe is None or recipe.base_servings <= 0:
                continue
            scale = Decimal(entry.planned_servings) / Decimal(recipe.base_servings)
            for ing in recipe.ingredients:
                if ing.catalog_ingredient_id and ing.servings is not None:
                    cid = ing.catalog_ingredient_id
                    catalog_needed[cid] = catalog_needed.get(cid, Decimal("0")) + (ing.servings * scale)
                    catalog_meta.setdefault(cid, (ing.name, ing.unit))
                else:
                    key = (ing.name, ing.unit)
                    legacy_needed[key] = legacy_needed.get(key, Decimal("0")) + (ing.quantity * scale)

        # Catalog-keyed subtraction. Pantry rows linked to a catalog id are
        # converted into the same serving units the recipe uses, then summed
        # against the need. Pantry rows without a catalog ref skip this loop.
        pantry_by_catalog: Dict[str, List[InventoryItem]] = {}
        for item in pantry:
            if item.catalog_ingredient_id:
                pantry_by_catalog.setdefault(item.catalog_ingredient_id, []).append(item)

        for cid, needed_servings in list(catalog_needed.items()):
            _name, target_label = catalog_meta[cid]
            available = Decimal("0")
            for pantry_item in pantry_by_catalog.get(cid, []):
                servings = _convert_to_servings(
                    quantity=pantry_item.quantity,
                    recipe_unit=pantry_item.unit,
                    catalog_serving_label=target_label,
                )
                if servings is not None:
                    available += servings
            catalog_needed[cid] = needed_servings - available

        # Legacy subtraction by (name, unit) — only for pantry rows
        # without a catalog ref (catalog-linked rows already counted above,
        # so we don't want to subtract them twice via name match too).
        for item in pantry:
            if item.catalog_ingredient_id:
                continue
            key = (item.name, item.unit)
            if key not in legacy_needed:
                continue
            legacy_needed[key] -= item.quantity

        out: List[GroceryListItem] = []
        for cid, remaining in catalog_needed.items():
            if remaining <= 0:
                continue
            name, label = catalog_meta[cid]
            qty_str, unit_str = _format_catalog_need(remaining, label)
            out.append(GroceryListItem(
                name=name,
                display_amount=qty_str,
                actual_need=qty_str,
                unit=unit_str,
            ))
        for (name, unit), qty in legacy_needed.items():
            if qty <= 0:
                continue
            qstr = _format_quantity(qty)
            out.append(GroceryListItem(
                name=name, display_amount=qstr, actual_need=qstr, unit=unit,
            ))

        out.sort(key=lambda i: (i.name.lower(), i.unit))
        return out


def _format_catalog_need(servings: Decimal, serving_label: str) -> Tuple[str, str]:
    """Render a catalog-backed shopping need in the most natural shopping
    units the catalog's serving_label allows.

    - "100g" → grams (e.g. 3.5 servings → "350 g").
    - "100 ml" → millilitres.
    - per-piece labels ("piece", "1 large egg", etc.) → integer count
      with the serving label as unit.
    - anything else → raw servings + label as unit (honest fallback).
    """
    label = (serving_label or "").strip().lower()
    if label in ("100g", "100 g"):
        grams = servings * Decimal("100")
        return _format_quantity(grams), "g"
    if label in ("100ml", "100 ml"):
        ml = servings * Decimal("100")
        return _format_quantity(ml), "ml"
    if label == "piece" or label.startswith("1 "):
        # Per-piece. Round up to the nearest whole piece since you can't
        # buy 2.4 eggs at the store; better to over-buy than underbuy.
        from math import ceil
        whole = ceil(float(servings))
        return str(whole), serving_label
    return _format_quantity(servings), serving_label


def _format_quantity(qty: Decimal) -> str:
    """Render a Decimal without trailing zeros (e.g. '2' not '2.00')."""
    normalized = qty.normalize()
    # normalize() can produce scientific notation for whole numbers; force plain.
    return f"{normalized:f}" if normalized == normalized.to_integral_value() else str(normalized)
