"""
Tests for MealPlanningService — the actual public API.

This file replaces an earlier version that called several methods
(`create_daily_meal_plan`, `create_weekly_meal_plan`, `adjust_meal_plan_for_calorie_banking`,
`get_meal_plan_summary`) that were never implemented on the service. The tests here
exercise what's really there.
"""
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date

sys.path.append(str(Path(__file__).parent.parent))

from core.services.meal_planning_service import MealPlanningService, FoodItem
from core.domain.models import Recipe, Ingredient, InventoryItem


def _recipe(name: str, calories: int, ingredients=None) -> Recipe:
    return Recipe(
        name=name,
        ingredients=ingredients or [Ingredient("chicken_breast", Decimal('6'), "oz")],
        base_servings=1,
        calories_per_serving=calories,
    )


def test_search_food_database_by_query_substring_match():
    service = MealPlanningService()
    results = service.search_food_database("almond")
    assert len(results) == 1
    assert results[0].name == "Almonds"
    assert results[0].calories_per_unit == 160
    assert results[0].unit == "oz"


def test_search_food_database_filters_by_category():
    service = MealPlanningService()
    fruits = service.search_food_database("", category="fruit")
    assert len(fruits) >= 2
    assert all(food.category == "fruit" for food in fruits)


def test_search_food_database_no_match_returns_empty():
    service = MealPlanningService()
    assert service.search_food_database("nonexistent_food_xyz") == []


def test_add_recipe_to_meal_plan_computes_calories_from_servings():
    service = MealPlanningService()
    recipe = _recipe("Chicken Bowl", calories=400)

    entry = service.add_recipe_to_meal_plan(
        "user1", date.today(), "lunch", recipe, Decimal('2'),
    )

    assert entry.item_type == "recipe"
    assert entry.recipe is recipe
    assert entry.servings == Decimal('2')
    assert entry.calories == 800  # 400 * 2
    # _estimate_recipe_macros uses 30/40/30 split → 4/4/9 cal/g
    assert entry.protein_grams == Decimal('800') * Decimal('0.30') / 4
    assert entry.carb_grams == Decimal('800') * Decimal('0.40') / 4
    assert entry.fat_grams == Decimal('800') * Decimal('0.30') / 9


def test_add_food_item_to_meal_plan_scales_macros_by_quantity():
    service = MealPlanningService()
    almonds = service.search_food_database("almond")[0]

    entry = service.add_food_item_to_meal_plan(
        "user1", date.today(), "snack", almonds, Decimal('2'),
    )

    assert entry.item_type == "food_item"
    assert entry.food_item is almonds
    assert entry.quantity == Decimal('2')
    # Almonds: 160 cal, 6/6/14 protein/carbs/fats per oz
    assert entry.calories == 320
    assert entry.protein_grams == Decimal('12')
    assert entry.carb_grams == Decimal('12')
    assert entry.fat_grams == Decimal('28')


def test_calculate_recipe_meal_coverage_whole_meals_and_leftovers():
    service = MealPlanningService()
    recipe = _recipe("Stir Fry", calories=400)

    # 6 servings made, 600 cal target per meal → 1.5 servings per meal → 4 whole meals
    coverage = service.calculate_recipe_meal_coverage(
        recipe, servings_made=Decimal('6'), target_calories_per_meal=600,
    )

    assert coverage["whole_meals_covered"] == 4
    assert coverage["days_covered"] == 4
    assert coverage["servings_per_meal"] == 1.5
    assert coverage["calories_per_serving"] == 400
    # 6 - (4 * 1.5) = 0 leftover servings
    assert coverage["leftover_servings"] == 0.0
    assert coverage["leftover_calories"] == 0
    assert coverage["total_calories"] == 2400


def test_calculate_recipe_meal_coverage_with_partial_leftovers():
    service = MealPlanningService()
    recipe = _recipe("Stir Fry", calories=500)

    # 5 servings made, 500 cal target per meal → 1 serving per meal → 5 whole meals, no leftovers
    coverage = service.calculate_recipe_meal_coverage(
        recipe, servings_made=Decimal('5'), target_calories_per_meal=500,
    )
    assert coverage["whole_meals_covered"] == 5
    assert coverage["leftover_servings"] == 0.0


def test_create_daily_meal_plan_aggregates_calories_and_macros():
    service = MealPlanningService()
    recipe = _recipe("Bowl", calories=500)
    almonds = service.search_food_database("almond")[0]

    entries = [
        service.add_recipe_to_meal_plan("u", date.today(), "lunch", recipe, Decimal('1')),
        service.add_food_item_to_meal_plan("u", date.today(), "snack", almonds, Decimal('1')),
    ]

    plan = service.create_daily_meal_plan_from_entries(
        "u", date.today(), target_calories=2000, meal_entries=entries,
    )

    assert plan.user_id == "u"
    assert plan.target_calories == 2000
    assert plan.total_calories == 660  # 500 + 160
    assert plan.calories_remaining == 1340
    assert len(plan.meals) == 2


def test_create_daily_meal_plan_with_no_entries():
    service = MealPlanningService()
    plan = service.create_daily_meal_plan_from_entries(
        "u", date.today(), target_calories=2000, meal_entries=[],
    )
    assert plan.total_calories == 0
    assert plan.calories_remaining == 2000
    assert plan.meals == []


def test_generate_comprehensive_grocery_list_combines_recipes_and_foods():
    service = MealPlanningService()
    recipe = Recipe(
        name="Protein Bowl",
        ingredients=[
            Ingredient("chicken_breast", Decimal('6'), "oz"),
            Ingredient("rice", Decimal('1'), "cup"),
        ],
        base_servings=1,
        calories_per_serving=500,
    )

    recipe_entry = service.add_recipe_to_meal_plan(
        "u", date.today(), "lunch", recipe, Decimal('2'),
    )
    almonds = service.search_food_database("almond")[0]
    banana = service.search_food_database("banana")[0]
    almond_entry = service.add_food_item_to_meal_plan(
        "u", date.today(), "snack", almonds, Decimal('2'),
    )
    banana_entry = service.add_food_item_to_meal_plan(
        "u", date.today(), "snack", banana, Decimal('1'),
    )

    plan = service.create_daily_meal_plan_from_entries(
        "u", date.today(), 2000, [recipe_entry, almond_entry, banana_entry],
    )

    inventory = [InventoryItem("rice", Decimal('0.5'), "cup")]
    grocery_list = service.generate_comprehensive_grocery_list([plan], inventory)

    item_names = [item.name.lower() for item in grocery_list]
    assert any("chicken" in n for n in item_names), item_names
    assert any("almond" in n for n in item_names), item_names
    assert any("banana" in n for n in item_names), item_names


def test_generate_comprehensive_grocery_list_aggregates_repeated_food_items():
    service = MealPlanningService()
    almonds = service.search_food_database("almond")[0]
    e1 = service.add_food_item_to_meal_plan("u", date.today(), "snack", almonds, Decimal('2'))
    e2 = service.add_food_item_to_meal_plan("u", date.today(), "snack", almonds, Decimal('3'))

    plan = service.create_daily_meal_plan_from_entries("u", date.today(), 2000, [e1, e2])
    grocery_list = service.generate_comprehensive_grocery_list([plan], [])

    almond_items = [i for i in grocery_list if "almond" in i.name.lower()]
    assert len(almond_items) == 1
    assert "5" in almond_items[0].display_amount  # 2 + 3 oz aggregated
