#!/usr/bin/env python3
"""
Backfill recipe ingredients with real catalog references.

For each recipe in a household whose ingredients are still legacy free-text
rows (no catalog_ingredient_id), this tool searches USDA + Open Food Facts
for the best match, converts the recipe's quantity+unit into "servings of
the catalog item", and saves the link back to the recipe. Anything it
can't auto-match is left alone and surfaced in the report — the planner
can fix individual lines through the food picker.

Usage:
    python scripts/backfill_recipes.py [--db PATH] [--household-id ID]
                                       [--all-households] [--offline]

Examples:
    # Backfill every recipe in the default-location DB.
    python scripts/backfill_recipes.py --all-households

    # Dry-run an offline backfill (sample DB only — no network calls).
    python scripts/backfill_recipes.py --all-households --offline

    # Target one household.
    python scripts/backfill_recipes.py --household-id 1234-...
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make the src/ tree importable when running this from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core.services.food_database_service import FoodDatabaseService
from core.services.seed_recipe_backfiller import (
    BackfillReport,
    SeedRecipeBackfiller,
)
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.recipe_repository import SQLiteRecipeRepository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.environ.get("MEAL_PLANNER_DB", "meal_planner.db"),
                        help="Path to the SQLite DB (defaults to MEAL_PLANNER_DB env or meal_planner.db).")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--household-id", help="Backfill only this household.")
    target.add_argument("--all-households", action="store_true",
                        help="Backfill every household in the DB.")
    parser.add_argument("--offline", action="store_true",
                        help="Skip USDA / Open Food Facts; use only the offline sample DB.")
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        print(f"DB file not found: {db_path}", file=sys.stderr)
        return 1

    food_db = FoodDatabaseService(network_enabled=not args.offline)
    catalog_repo = SQLiteIngredientCatalogRepository(db_path)
    recipe_repo = SQLiteRecipeRepository(db_path)
    backfiller = SeedRecipeBackfiller(food_db, catalog_repo, recipe_repo)

    if args.household_id:
        household_ids = [args.household_id]
    else:
        # Walk every household in the DB.
        household_repo = SQLiteHouseholdRepository(db_path)
        with household_repo.db_manager.get_connection() as conn:
            household_ids = [r["id"] for r in conn.execute("SELECT id FROM households").fetchall()]

    if not household_ids:
        print("No households to backfill.")
        return 0

    grand_matched = 0
    grand_skipped = 0
    for hid in household_ids:
        print(f"\n=== Household {hid} ===")
        report = backfiller.backfill_household(hid)
        _print_report(report)
        grand_matched += report.total_ingredients_matched
        grand_skipped += report.total_ingredients_skipped

    print(f"\nDone. Matched: {grand_matched}, Skipped: {grand_skipped}.")
    if grand_skipped:
        print("Skipped ingredients are still showing as legacy free-text in the UI. "
              "Edit those recipes through the food picker to fix them individually.")
    return 0


def _print_report(report: BackfillReport) -> None:
    if not report.recipe_results:
        print("  (no recipes)")
        return
    for r in report.recipe_results:
        cal_str = f"{r.new_calories_per_serving} cal/serving" if r.new_calories_per_serving else "(unchanged)"
        print(f"  • {r.recipe_name}: matched {r.matched_count}, "
              f"skipped {r.skipped_count}  →  {cal_str}")
        for ing in r.ingredient_results:
            if ing.matched:
                qty = float(ing.servings) if ing.servings is not None else 0
                print(f"      ✓ {ing.ingredient_name!r:40s} → "
                      f"{qty:.2f} × {ing.catalog_name}")
            else:
                print(f"      ✗ {ing.ingredient_name!r:40s} → skipped: {ing.skip_reason}")


if __name__ == "__main__":
    raise SystemExit(main())
