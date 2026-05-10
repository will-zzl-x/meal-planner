"""
PantryCoverageService — answers "what fraction of this recipe's
ingredients do I already have on hand?"

Per recipe ingredient with a catalog_ingredient_id:
- Find pantry rows with the same catalog_ingredient_id (per household).
- Convert each pantry row's `(quantity, unit)` to catalog servings via
  `_convert_to_servings` (reused from seed_recipe_backfiller). Sum.
- Compare to the recipe's `servings` count for that ingredient.
- "have" if pantry servings ≥ recipe servings, else "short" (with
  the deficit reported), else "missing" (no pantry rows at all).

Ingredients without a catalog_ingredient_id are reported as `unknown`
and excluded from the coverage ratio (we have no way to compare them).

`treat_staples_as_available=True` short-circuits any line whose catalog
display name contains a substring from a hard-coded staples list
(salt, pepper, oil, etc.) so the coverage score isn't dragged down
by always-on-hand items the user hasn't bothered to log.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from core.domain.models import Ingredient, Recipe
from core.services.seed_recipe_backfiller import _convert_to_servings
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


# Common-staple substrings. Case-insensitive. Hit any of these and the
# line is treated as available when the toggle is on. Hard-coded for
# V2; per-household configuration is a V3 nice-to-have.
STAPLE_NAMES = frozenset({
    "salt", "pepper", "olive oil", "vegetable oil", "avocado oil",
    "sesame oil", "grape seed oil", "butter", "garlic powder",
    "onion powder", "water", "sugar", "flour", "cornstarch",
    "baking powder", "baking soda",
})


@dataclass
class CoverageLine:
    """One ingredient's coverage outcome."""
    ingredient_name: str
    status: str  # "have" | "short" | "missing" | "unknown" | "staple"
    needed_servings: Optional[Decimal] = None
    available_servings: Optional[Decimal] = None
    catalog_display_name: Optional[str] = None
    deficit: Optional[Decimal] = None  # Set when status == "short".


@dataclass
class CoverageReport:
    lines: List[CoverageLine] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        """Number of catalog-backed lines (excludes unknown legacy rows).
        This is the denominator for `coverage_ratio`."""
        return sum(1 for ln in self.lines if ln.status != "unknown")

    @property
    def have_count(self) -> int:
        return sum(1 for ln in self.lines if ln.status in ("have", "staple"))

    @property
    def missing_count(self) -> int:
        """Lines we know we don't have enough of (short or fully missing)."""
        return sum(1 for ln in self.lines if ln.status in ("short", "missing"))

    @property
    def unknown_count(self) -> int:
        return sum(1 for ln in self.lines if ln.status == "unknown")

    @property
    def coverage_ratio(self) -> float:
        """have / total (catalog-backed only). 1.0 for all-have / empty
        recipes; the only-unknown case returns 0.0 so it doesn't pretend
        to perfect coverage."""
        total = self.total_count
        if total == 0:
            return 0.0
        return self.have_count / total

    @property
    def missing_lines(self) -> List[CoverageLine]:
        """For UI display under 'Missing from pantry'."""
        return [ln for ln in self.lines if ln.status in ("short", "missing")]


class PantryCoverageService:
    def __init__(self,
                 inventory_repo: SQLiteInventoryRepository,
                 catalog_repo: SQLiteIngredientCatalogRepository):
        self.inventory_repo = inventory_repo
        self.catalog_repo = catalog_repo

    def compute_coverage(self,
                         recipe: Recipe,
                         household_id: str,
                         *,
                         treat_staples_as_available: bool = False) -> CoverageReport:
        """Walk the recipe's ingredients and report per-line coverage."""
        report = CoverageReport()
        # Pre-fetch the household's pantry once and bucket by catalog ref.
        pantry_by_catalog = self._pantry_by_catalog(household_id)

        for ingredient in recipe.ingredients:
            line = self._coverage_for(
                ingredient, pantry_by_catalog,
                treat_staples_as_available=treat_staples_as_available,
            )
            report.lines.append(line)
        return report

    # ------------------------------------------------- internals

    def _pantry_by_catalog(self, household_id: str) -> dict:
        """Build a dict mapping catalog_ingredient_id → list of
        InventoryItems for fast lookup during coverage computation."""
        out: dict = {}
        for item in self.inventory_repo.get_household_inventory(household_id):
            if item.catalog_ingredient_id:
                out.setdefault(item.catalog_ingredient_id, []).append(item)
        return out

    def _coverage_for(self,
                      ingredient: Ingredient,
                      pantry_by_catalog: dict,
                      *,
                      treat_staples_as_available: bool) -> CoverageLine:
        if not ingredient.catalog_ingredient_id or ingredient.servings is None:
            # Legacy free-text ingredient — we can't make a comparison.
            return CoverageLine(
                ingredient_name=ingredient.name,
                status="unknown",
            )

        catalog = self.catalog_repo.find_by_id(ingredient.catalog_ingredient_id)
        if catalog is None:
            # Catalog row vanished — treat as unknown rather than crash.
            return CoverageLine(
                ingredient_name=ingredient.name,
                status="unknown",
            )

        # Staples short-circuit: salt etc. are always "have" when the
        # user opts in.
        if treat_staples_as_available and _is_staple(catalog.name):
            return CoverageLine(
                ingredient_name=ingredient.name,
                status="staple",
                needed_servings=ingredient.servings,
                catalog_display_name=catalog.display_name,
            )

        pantry_rows = pantry_by_catalog.get(ingredient.catalog_ingredient_id, [])
        if not pantry_rows:
            return CoverageLine(
                ingredient_name=ingredient.name,
                status="missing",
                needed_servings=ingredient.servings,
                catalog_display_name=catalog.display_name,
            )

        # Sum pantry servings across all matching rows.
        available = Decimal("0")
        for row in pantry_rows:
            servings = _convert_to_servings(
                quantity=row.quantity,
                recipe_unit=row.unit,
                catalog_serving_label=catalog.serving_label,
            )
            if servings is not None:
                available += servings

        if available >= ingredient.servings:
            return CoverageLine(
                ingredient_name=ingredient.name,
                status="have",
                needed_servings=ingredient.servings,
                available_servings=available,
                catalog_display_name=catalog.display_name,
            )

        return CoverageLine(
            ingredient_name=ingredient.name,
            status="short",
            needed_servings=ingredient.servings,
            available_servings=available,
            deficit=ingredient.servings - available,
            catalog_display_name=catalog.display_name,
        )


def _is_staple(catalog_name: str) -> bool:
    """Case-insensitive substring match against the staple list. Cheap
    and deterministic — exact name matching would require maintaining a
    separate canonical staples table per catalog source."""
    name = (catalog_name or "").lower()
    return any(staple in name for staple in STAPLE_NAMES)
