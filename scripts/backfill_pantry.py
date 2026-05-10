#!/usr/bin/env python3
"""
Backfill legacy pantry rows with catalog references.

For each pantry row whose `catalog_ingredient_id` is NULL, this tool
searches USDA + Open Food Facts for the row's name, takes the top match,
and updates the row in place. Anything it can't auto-match is left
alone and surfaced in the report — the user can fix individual rows
through the pantry UI's "Link to a food database entry" expander.

Usage:
    python scripts/backfill_pantry.py [--db PATH] [--household-id ID]
                                      [--all-households] [--offline]

Examples:
    # Backfill every household's pantry in the default DB.
    python scripts/backfill_pantry.py --all-households

    # Dry-run offline (sample DB only, no network).
    python scripts/backfill_pantry.py --all-households --offline
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make src/ importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.services.food_database_service import FoodDatabaseService
from core.services.pantry_backfiller import PantryBackfillReport, PantryBackfiller
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", default=os.environ.get("MEAL_PLANNER_DB", "meal_planner.db"),
                        help="Path to the SQLite DB (defaults to MEAL_PLANNER_DB or meal_planner.db).")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--household-id", help="Backfill only this household.")
    target.add_argument("--all-households", action="store_true",
                        help="Backfill every household in the DB.")
    parser.add_argument("--offline", action="store_true",
                        help="Skip USDA / OFF; use only the offline sample DB.")
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        print(f"DB file not found: {db_path}", file=sys.stderr)
        return 1

    food_db = FoodDatabaseService(network_enabled=not args.offline)
    catalog = SQLiteIngredientCatalogRepository(db_path)
    inv = SQLiteInventoryRepository(db_path)
    bf = PantryBackfiller(food_db, catalog, inv)

    if args.household_id:
        household_ids = [args.household_id]
    else:
        households = SQLiteHouseholdRepository(db_path)
        with households.db_manager.get_connection() as conn:
            household_ids = [r["id"] for r in conn.execute("SELECT id FROM households").fetchall()]

    if not household_ids:
        print("No households to backfill.")
        return 0

    grand_matched = 0
    grand_skipped = 0
    for hid in household_ids:
        print(f"\n=== Household {hid} ===")
        report = bf.backfill_household(hid)
        _print_report(report)
        grand_matched += report.matched_count
        grand_skipped += report.skipped_count

    print(f"\nDone. Matched: {grand_matched}, Skipped: {grand_skipped}.")
    if grand_skipped:
        print("Skipped items still show as legacy free-text. Link them via "
              "the Pantry page's 'Link to a food database entry' expander.")
    return 0


def _print_report(report: PantryBackfillReport) -> None:
    if not report.item_results:
        print("  (empty pantry)")
        return
    for r in report.item_results:
        if r.matched:
            print(f"  ✓ {r.item_name!r:40s} → {r.catalog_name}")
        else:
            print(f"  ✗ {r.item_name!r:40s} → skipped: {r.skip_reason}")


if __name__ == "__main__":
    raise SystemExit(main())
