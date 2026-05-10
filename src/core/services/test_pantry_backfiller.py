"""Tests for PantryBackfiller (V2-4)."""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import InventoryItem
from core.services.food_database_service import FoodDatabaseService
from core.services.pantry_backfiller import PantryBackfiller
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


def _setup(tmp_path):
    db = str(tmp_path / "pantry_bf.db")
    households = SQLiteHouseholdRepository(db)
    inv = SQLiteInventoryRepository(db)
    catalog = SQLiteIngredientCatalogRepository(db)
    food_db = FoodDatabaseService(network_enabled=False)  # offline sample only
    bf = PantryBackfiller(food_db, catalog, inv)
    h = households.create("Smiths")
    return h, inv, catalog, bf


def test_links_legacy_pantry_row_to_catalog(tmp_path):
    h, inv, _, bf = _setup(tmp_path)
    # Legacy free-text pantry row, no catalog ref.
    inv.add_inventory_item(h.id, InventoryItem(
        name="chicken breast", quantity=Decimal("2"), unit="lb"))

    report = bf.backfill_household(h.id)
    assert report.matched_count == 1
    assert report.skipped_count == 0

    [reloaded] = inv.get_household_inventory(h.id)
    assert reloaded.catalog_ingredient_id is not None
    # User-typed name and quantity/unit are preserved.
    assert reloaded.name == "chicken breast"
    assert reloaded.quantity == Decimal("2")
    assert reloaded.unit == "lb"


def test_unmatched_item_left_alone(tmp_path):
    h, inv, _, bf = _setup(tmp_path)
    inv.add_inventory_item(h.id, InventoryItem(
        name="flux capacitor dust", quantity=Decimal("1"), unit="cup"))

    report = bf.backfill_household(h.id)
    assert report.matched_count == 0
    assert report.skipped_count == 1
    assert report.item_results[0].skip_reason == "no match in food database"

    [reloaded] = inv.get_household_inventory(h.id)
    assert reloaded.catalog_ingredient_id is None


def test_already_linked_item_is_skipped(tmp_path):
    h, inv, _, bf = _setup(tmp_path)
    inv.add_inventory_item(h.id, InventoryItem(
        name="rice", quantity=Decimal("3"), unit="cup",
        catalog_ingredient_id="cat-existing"))

    report = bf.backfill_household(h.id)
    assert report.matched_count == 1
    assert report.skipped_count == 0
    # Catalog id unchanged.
    [reloaded] = inv.get_household_inventory(h.id)
    assert reloaded.catalog_ingredient_id == "cat-existing"


def test_idempotent_re_run(tmp_path):
    h, inv, _, bf = _setup(tmp_path)
    inv.add_inventory_item(h.id, InventoryItem(
        name="chicken breast", quantity=Decimal("2"), unit="lb"))

    first = bf.backfill_household(h.id)
    second = bf.backfill_household(h.id)

    assert first.matched_count == 1
    assert second.matched_count == 1  # already linked → counted matched
    # Catalog ref stable across runs.
    [item_after_first] = inv.get_household_inventory(h.id)
    [item_after_second] = inv.get_household_inventory(h.id)
    assert item_after_first.catalog_ingredient_id == item_after_second.catalog_ingredient_id
