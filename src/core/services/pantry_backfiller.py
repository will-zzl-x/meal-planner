"""
Best-effort backfill of legacy free-text pantry rows into catalog-linked
ones. Mirrors the shape of `seed_recipe_backfiller` for recipe ingredients.

Strategy per pantry row:
1. If `catalog_ingredient_id` is already set — leave it alone (idempotent).
2. Search FoodDatabaseService for the item's name with progressively
   simpler queries. Reuses the candidate-query helpers from
   `seed_recipe_backfiller`.
3. Take the top match and persist it as a catalog row (idempotent on
   source+external_id).
4. Update the inventory row with the new catalog_ingredient_id. The
   user-typed name, quantity and unit are preserved.

Anything that can't be matched is left alone and surfaced in the report
so the user knows which rows still need a manual link via the pantry UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from core.domain.models import CatalogIngredient, FoodItem, InventoryItem
from core.services.food_database_service import FoodDatabaseService
from core.services.seed_recipe_backfiller import _candidate_queries
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


@dataclass
class PantryItemResolution:
    item_name: str
    matched: bool
    catalog_id: Optional[str] = None
    catalog_name: Optional[str] = None
    skip_reason: Optional[str] = None  # When matched=False.


@dataclass
class PantryBackfillReport:
    item_results: List[PantryItemResolution] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.item_results)

    @property
    def matched_count(self) -> int:
        return sum(1 for r in self.item_results if r.matched)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.item_results if not r.matched)


class PantryBackfiller:
    def __init__(self,
                 food_db: FoodDatabaseService,
                 catalog_repo: SQLiteIngredientCatalogRepository,
                 inventory_repo: SQLiteInventoryRepository):
        self.food_db = food_db
        self.catalog_repo = catalog_repo
        self.inventory_repo = inventory_repo

    def backfill_household(self, household_id: str) -> PantryBackfillReport:
        """Try to attach a catalog reference to every still-unlinked
        pantry row for a household. Idempotent — already-linked rows are
        skipped on subsequent runs."""
        report = PantryBackfillReport()
        items = self.inventory_repo.get_household_inventory(household_id)
        for item in items:
            if item.catalog_ingredient_id:
                # Already linked — count as matched but don't touch.
                report.item_results.append(PantryItemResolution(
                    item_name=item.name,
                    matched=True,
                    catalog_id=item.catalog_ingredient_id,
                    catalog_name=item.name,
                ))
                continue

            food_match = self._find_food_match(item.name)
            if food_match is None:
                report.item_results.append(PantryItemResolution(
                    item_name=item.name,
                    matched=False,
                    skip_reason="no match in food database",
                ))
                continue

            catalog = self.catalog_repo.save(CatalogIngredient.from_food_item(food_match))
            # Persist the linked row by re-adding (the repo upserts on
            # name+unit and overwrites catalog_ingredient_id on update).
            self.inventory_repo.add_inventory_item(
                household_id,
                InventoryItem(
                    name=item.name,
                    quantity=item.quantity,
                    unit=item.unit,
                    catalog_ingredient_id=catalog.id,
                ),
            )
            report.item_results.append(PantryItemResolution(
                item_name=item.name,
                matched=True,
                catalog_id=catalog.id,
                catalog_name=catalog.display_name,
            ))
        return report

    def _find_food_match(self, item_name: str) -> Optional[FoodItem]:
        for query in _candidate_queries(item_name):
            results = self.food_db.search_food_database(query, limit=8)
            if results:
                return results[0]
        return None
