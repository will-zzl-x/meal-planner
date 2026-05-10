"""Tests for PantryCoverageService (V2-5)."""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import CatalogIngredient, Ingredient, InventoryItem, Recipe
from core.services.pantry_coverage_service import PantryCoverageService
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.ingredient_catalog_repository import (
    SQLiteIngredientCatalogRepository,
)
from repositories.sqlite.inventory_repository import SQLiteInventoryRepository


def _setup(tmp_path):
    db = str(tmp_path / "cov.db")
    households = SQLiteHouseholdRepository(db)
    inv = SQLiteInventoryRepository(db)
    catalog = SQLiteIngredientCatalogRepository(db)
    h = households.create("Smiths")
    return h, inv, catalog, PantryCoverageService(inv, catalog)


def _seed_catalog(catalog: SQLiteIngredientCatalogRepository,
                  *, name: str, label: str = "100g",
                  external_id: str = "x") -> str:
    saved = catalog.save(CatalogIngredient(
        id="", name=name, serving_label=label,
        calories_per_serving=100, source="usda", external_id=external_id,
    ))
    return saved.id


# ------------------------------------------------- have / short / missing

def test_have_when_pantry_meets_recipe_demand(tmp_path):
    h, inv, catalog, svc = _setup(tmp_path)
    cid = _seed_catalog(catalog, name="Chicken Breast", external_id="c1")
    # 1 lb chicken in pantry. Recipe wants 1 serving of 100g (~100g).
    # 1 lb = 453.59 g → 4.5 servings of 100g. We have plenty.
    inv.add_inventory_item(h.id, InventoryItem(
        name="chicken", quantity=Decimal("1"), unit="lb",
        catalog_ingredient_id=cid))

    recipe = Recipe(
        name="X",
        ingredients=[Ingredient(name="chicken", quantity=Decimal("1"),
                                unit="100g", catalog_ingredient_id=cid,
                                servings=Decimal("1"))],
        base_servings=1, calories_per_serving=0,
    )
    report = svc.compute_coverage(recipe, h.id)
    assert report.have_count == 1
    assert report.coverage_ratio == 1.0
    assert report.lines[0].status == "have"


def test_short_when_pantry_below_demand(tmp_path):
    h, inv, catalog, svc = _setup(tmp_path)
    cid = _seed_catalog(catalog, name="Chicken Breast", external_id="c1")
    # 100 g pantry = 1 serving; recipe wants 3.
    inv.add_inventory_item(h.id, InventoryItem(
        name="chicken", quantity=Decimal("100"), unit="g",
        catalog_ingredient_id=cid))
    recipe = Recipe(
        name="X",
        ingredients=[Ingredient(name="chicken", quantity=Decimal("3"),
                                unit="100g", catalog_ingredient_id=cid,
                                servings=Decimal("3"))],
        base_servings=1, calories_per_serving=0,
    )
    report = svc.compute_coverage(recipe, h.id)
    assert report.lines[0].status == "short"
    assert report.lines[0].deficit == Decimal("2")  # need 3, have 1
    assert report.coverage_ratio == 0.0


def test_missing_when_no_pantry_match(tmp_path):
    h, inv, catalog, svc = _setup(tmp_path)
    cid = _seed_catalog(catalog, name="Salmon Fillet", external_id="s1")
    recipe = Recipe(
        name="X",
        ingredients=[Ingredient(name="salmon", quantity=Decimal("1"),
                                unit="100g", catalog_ingredient_id=cid,
                                servings=Decimal("1"))],
        base_servings=1, calories_per_serving=0,
    )
    report = svc.compute_coverage(recipe, h.id)
    assert report.lines[0].status == "missing"
    assert report.coverage_ratio == 0.0


def test_unknown_legacy_ingredient_does_not_count_against_coverage(tmp_path):
    h, inv, catalog, svc = _setup(tmp_path)
    cid = _seed_catalog(catalog, name="Chicken Breast", external_id="c1")
    inv.add_inventory_item(h.id, InventoryItem(
        name="chicken", quantity=Decimal("1"), unit="lb",
        catalog_ingredient_id=cid))

    # Recipe has one catalog-backed ingredient and one legacy free-text.
    recipe = Recipe(
        name="X",
        ingredients=[
            Ingredient(name="chicken", quantity=Decimal("1"), unit="100g",
                       catalog_ingredient_id=cid, servings=Decimal("1")),
            Ingredient(name="vibes", quantity=Decimal("1"), unit="tsp"),
        ],
        base_servings=1, calories_per_serving=0,
    )
    report = svc.compute_coverage(recipe, h.id)
    assert report.have_count == 1
    assert report.unknown_count == 1
    assert report.total_count == 1  # excludes unknown
    assert report.coverage_ratio == 1.0


def test_staples_toggle_marks_salt_as_available_without_pantry_row(tmp_path):
    h, inv, catalog, svc = _setup(tmp_path)
    salt_id = _seed_catalog(catalog, name="Salt", external_id="salt1")
    recipe = Recipe(
        name="X",
        ingredients=[Ingredient(name="salt", quantity=Decimal("1"),
                                unit="100g", catalog_ingredient_id=salt_id,
                                servings=Decimal("0.01"))],
        base_servings=1, calories_per_serving=0,
    )
    # Without toggle: pantry has no salt → missing.
    no_toggle = svc.compute_coverage(recipe, h.id, treat_staples_as_available=False)
    assert no_toggle.lines[0].status == "missing"
    # With toggle: salt is treated as available even though pantry is empty.
    with_toggle = svc.compute_coverage(recipe, h.id, treat_staples_as_available=True)
    assert with_toggle.lines[0].status == "staple"
    assert with_toggle.coverage_ratio == 1.0


def test_empty_recipe_has_zero_coverage_ratio(tmp_path):
    """A recipe whose ingredients are entirely legacy free-text reports
    coverage_ratio=0.0 (since total_count is 0). The UI should treat
    that as 'unknown / can't say' rather than rendering the chip."""
    h, inv, catalog, svc = _setup(tmp_path)
    recipe = Recipe(
        name="Legacy",
        ingredients=[Ingredient(name="rice", quantity=Decimal("1"), unit="cup")],
        base_servings=1, calories_per_serving=0,
    )
    report = svc.compute_coverage(recipe, h.id)
    assert report.total_count == 0
    assert report.coverage_ratio == 0.0
