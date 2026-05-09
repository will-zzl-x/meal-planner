"""Tests for GroceryListService — plan + pantry → grocery list."""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.domain.models import Ingredient, InventoryItem, Recipe
from core.interfaces.meal_plan_repository import MealPlanEntry
from core.services.grocery_list_service import GroceryListService


def _entry(recipe_id: str, servings: int, meal: str = "lunch") -> MealPlanEntry:
    return MealPlanEntry(
        id=f"e-{recipe_id}-{meal}",
        recipe_id=recipe_id,
        planned_date=date(2026, 5, 11),  # arbitrary fixed date
        planned_servings=servings,
        meal_type=meal,
    )


def _recipe(rid: str, name: str, *ingredients: Ingredient, base_servings: int = 1) -> Recipe:
    r = Recipe(
        name=name,
        ingredients=list(ingredients),
        base_servings=base_servings,
        calories_per_serving=400,
    )
    r.id = rid
    return r


def test_empty_plan_returns_empty_list():
    svc = GroceryListService()
    assert svc.generate(entries=[], recipes_by_id={}, pantry=[]) == []


def test_single_recipe_one_serving_yields_its_ingredients():
    rid = "r1"
    recipes = {rid: _recipe(rid, "Bowl",
                            Ingredient("chicken breast", Decimal("6"), "oz"),
                            Ingredient("rice", Decimal("1"), "cup"))}
    svc = GroceryListService()
    items = svc.generate([_entry(rid, 1)], recipes, pantry=[])
    by_name = {i.name: i for i in items}
    assert by_name["chicken breast"].unit == "oz"
    assert by_name["chicken breast"].actual_need == "6"
    assert by_name["rice"].actual_need == "1"


def test_doubled_servings_scales_ingredients():
    rid = "r1"
    recipes = {rid: _recipe(rid, "Bowl",
                            Ingredient("chicken breast", Decimal("6"), "oz"),
                            base_servings=1)}
    svc = GroceryListService()
    items = svc.generate([_entry(rid, 2)], recipes, pantry=[])
    assert items[0].actual_need == "12"


def test_same_recipe_multiple_meal_slots_aggregate():
    rid = "r1"
    recipes = {rid: _recipe(rid, "Bowl",
                            Ingredient("rice", Decimal("1"), "cup"),
                            base_servings=1)}
    svc = GroceryListService()
    items = svc.generate(
        [_entry(rid, 1, "lunch"), _entry(rid, 1, "dinner")],
        recipes, pantry=[],
    )
    assert len(items) == 1
    assert items[0].actual_need == "2"


def test_different_recipes_aggregate_shared_ingredient():
    r1, r2 = "r1", "r2"
    recipes = {
        r1: _recipe(r1, "Bowl A", Ingredient("rice", Decimal("1"), "cup")),
        r2: _recipe(r2, "Bowl B", Ingredient("rice", Decimal("2"), "cup")),
    }
    svc = GroceryListService()
    items = svc.generate([_entry(r1, 1), _entry(r2, 1)], recipes, pantry=[])
    rice = next(i for i in items if i.name == "rice")
    assert rice.actual_need == "3"


def test_pantry_subtracts_from_need():
    rid = "r1"
    recipes = {rid: _recipe(rid, "Bowl",
                            Ingredient("rice", Decimal("3"), "cup"),
                            base_servings=1)}
    svc = GroceryListService()
    items = svc.generate(
        [_entry(rid, 1)], recipes,
        pantry=[InventoryItem(name="rice", quantity=Decimal("1"), unit="cup")],
    )
    assert items[0].actual_need == "2"


def test_pantry_fully_covering_drops_item():
    rid = "r1"
    recipes = {rid: _recipe(rid, "Bowl",
                            Ingredient("rice", Decimal("1"), "cup"),
                            base_servings=1)}
    svc = GroceryListService()
    items = svc.generate(
        [_entry(rid, 1)], recipes,
        pantry=[InventoryItem(name="rice", quantity=Decimal("5"), unit="cup")],
    )
    assert items == []


def test_pantry_with_mismatched_unit_does_not_subtract():
    """The V1 service treats different units as different items (no conversion)."""
    rid = "r1"
    recipes = {rid: _recipe(rid, "Bowl",
                            Ingredient("rice", Decimal("1"), "cup"),
                            base_servings=1)}
    svc = GroceryListService()
    items = svc.generate(
        [_entry(rid, 1)], recipes,
        # Pantry stores rice in lb, not cup → no overlap by (name, unit).
        pantry=[InventoryItem(name="rice", quantity=Decimal("5"), unit="lb")],
    )
    assert len(items) == 1
    assert items[0].actual_need == "1"


def test_unknown_recipe_id_is_skipped():
    svc = GroceryListService()
    items = svc.generate([_entry("ghost", 1)], recipes_by_id={}, pantry=[])
    assert items == []


def test_output_sorted_by_name():
    rid = "r1"
    recipes = {rid: _recipe(rid, "Bowl",
                            Ingredient("rice", Decimal("1"), "cup"),
                            Ingredient("chicken breast", Decimal("1"), "oz"),
                            Ingredient("oats", Decimal("1"), "cup"))}
    svc = GroceryListService()
    items = svc.generate([_entry(rid, 1)], recipes, pantry=[])
    assert [i.name for i in items] == ["chicken breast", "oats", "rice"]
