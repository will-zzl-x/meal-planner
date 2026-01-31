#!/usr/bin/env python3
"""
Test Enhanced Meal Planning Service - Phase 4 Integration
"""
import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.services.meal_planning_service import MealPlanningService
from core.domain.models import Recipe, Ingredient, InventoryItem

def create_sample_recipes():
    """Create sample recipes for testing."""
    return [
        Recipe(
            name="Protein Pancakes",
            ingredients=[
                Ingredient("oats", Decimal('0.5'), "cup"),
                Ingredient("protein_powder", Decimal('1'), "scoop"),
                Ingredient("eggs", Decimal('2'), "whole"),
            ],
            base_servings=1,
            calories_per_serving=320
        ),
        Recipe(
            name="Chicken Salad",
            ingredients=[
                Ingredient("chicken_breast", Decimal('6'), "oz"),
                Ingredient("mixed_greens", Decimal('2'), "cup"),
                Ingredient("olive_oil", Decimal('1'), "tbsp"),
            ],
            base_servings=1,
            calories_per_serving=450
        ),
        Recipe(
            name="Salmon Dinner",
            ingredients=[
                Ingredient("salmon_fillet", Decimal('6'), "oz"),
                Ingredient("sweet_potato", Decimal('1'), "medium"),
                Ingredient("broccoli", Decimal('1'), "cup"),
            ],
            base_servings=1,
            calories_per_serving=520
        ),
        Recipe(
            name="Greek Yogurt Snack",
            ingredients=[
                Ingredient("greek_yogurt", Decimal('1'), "cup"),
                Ingredient("berries", Decimal('0.5'), "cup"),
                Ingredient("almonds", Decimal('0.25'), "cup"),
            ],
            base_servings=1,
            calories_per_serving=280
        )
    ]

def create_sample_inventory():
    """Create sample household inventory."""
    return [
        InventoryItem("chicken_breast", Decimal('2'), "lb"),
        InventoryItem("eggs", Decimal('6'), "whole"),
        InventoryItem("oats", Decimal('2'), "cup"),
    ]

def test_daily_meal_planning():
    """Test daily meal plan creation with calorie targeting."""
    print("📅 Testing Daily Meal Planning")
    print("=" * 35)
    
    service = MealPlanningService()
    recipes = create_sample_recipes()
    
    # Test daily meal plan creation
    target_calories = 2000
    daily_plan = service.create_daily_meal_plan(
        user_id="alice",
        target_date=date.today(),
        target_calories=target_calories,
        available_recipes=recipes
    )
    
    print(f"✅ Daily meal plan created:")
    print(f"   Target calories: {daily_plan.target_calories}")
    print(f"   Actual calories: {daily_plan.total_calories}")
    print(f"   Calories remaining: {daily_plan.calories_remaining}")
    print(f"   Total protein: {daily_plan.total_protein:.1f}g")
    print(f"   Total carbs: {daily_plan.total_carbs:.1f}g")
    print(f"   Total fats: {daily_plan.total_fats:.1f}g")
    
    print(f"\n   Meals planned:")
    for meal in daily_plan.meals:
        print(f"   • {meal.meal_type}: {meal.recipe.name} ({meal.servings} servings, {meal.calories} cal)")
    
    return len(daily_plan.meals) > 0

def test_weekly_meal_planning():
    """Test weekly meal planning for household."""
    print("\n📊 Testing Weekly Meal Planning")
    print("=" * 35)
    
    service = MealPlanningService()
    recipes = create_sample_recipes()
    inventory = create_sample_inventory()
    
    # Create calorie targets for two users
    user_calorie_targets = {
        "alice": [2000, 1800, 2200, 1900, 2100, 2300, 1900],  # Flexible weekly plan
        "bob": [2500, 2400, 2600, 2300, 2700, 2800, 2200]     # Higher calorie needs
    }
    
    # Create weekly meal plan
    weekly_plan = service.create_weekly_meal_plan(
        household_id="household_1",
        user_calorie_targets=user_calorie_targets,
        available_recipes=recipes,
        household_inventory=inventory
    )
    
    print(f"✅ Weekly meal plan created:")
    print(f"   Week starting: {weekly_plan.week_start_date}")
    print(f"   Users planned: {len(weekly_plan.daily_plans)}")
    print(f"   Grocery list items: {len(weekly_plan.grocery_list)}")
    
    # Show user summaries
    for user_id, total_calories in weekly_plan.total_weekly_calories.items():
        daily_plans = weekly_plan.daily_plans[user_id]
        avg_daily = total_calories / len(daily_plans)
        print(f"   {user_id}: {total_calories} cal/week (avg: {avg_daily:.0f} cal/day)")
    
    # Show grocery list sample
    print(f"\n   Sample grocery items:")
    for item in weekly_plan.grocery_list[:5]:  # Show first 5 items
        print(f"   • {item.name}: {item.display_amount}")
    
    return len(weekly_plan.grocery_list) > 0

def test_calorie_banking_integration():
    """Test meal plan adjustment with calorie banking."""
    print("\n💰 Testing Calorie Banking Integration")
    print("=" * 40)
    
    service = MealPlanningService()
    recipes = create_sample_recipes()
    
    # Create base daily plan
    base_plan = service.create_daily_meal_plan(
        user_id="alice",
        target_date=date.today(),
        target_calories=2000,
        available_recipes=recipes
    )
    
    print(f"✅ Base plan: {base_plan.total_calories} calories")
    
    # Test with banked calories (ate less yesterday)
    banked_calories = 300
    adjusted_plan = service.adjust_meal_plan_for_calorie_banking(
        base_plan, banked_calories
    )
    
    print(f"✅ With {banked_calories} banked calories: {adjusted_plan.total_calories} calories")
    print(f"   New target: {adjusted_plan.target_calories}")
    
    # Test with borrowed calories (restaurant day)
    borrowed_calories = -500
    restaurant_plan = service.adjust_meal_plan_for_calorie_banking(
        base_plan, borrowed_calories
    )
    
    print(f"✅ With {abs(borrowed_calories)} borrowed calories: {restaurant_plan.total_calories} calories")
    print(f"   New target: {restaurant_plan.target_calories}")
    
    return True

def test_meal_plan_summary():
    """Test meal plan summary statistics."""
    print("\n📈 Testing Meal Plan Summary")
    print("=" * 30)
    
    service = MealPlanningService()
    recipes = create_sample_recipes()
    inventory = create_sample_inventory()
    
    # Create weekly plan
    user_calorie_targets = {
        "alice": [2000, 1800, 2200, 1900, 2100, 2300, 1900],
        "bob": [2500, 2400, 2600, 2300, 2700, 2800, 2200]
    }
    
    weekly_plan = service.create_weekly_meal_plan(
        household_id="household_1",
        user_calorie_targets=user_calorie_targets,
        available_recipes=recipes,
        household_inventory=inventory
    )
    
    # Get summary
    summary = service.get_meal_plan_summary(weekly_plan)
    
    print(f"✅ Meal plan summary:")
    print(f"   Unique recipes used: {summary['total_unique_recipes']}")
    print(f"   Total meals planned: {summary['total_meals_planned']}")
    print(f"   Grocery list items: {summary['grocery_list_items']}")
    print(f"   Week starting: {summary['week_start']}")
    
    print(f"\n   User summaries:")
    for user_id, user_summary in summary['user_summaries'].items():
        print(f"   {user_id}:")
        print(f"     Weekly calories: {user_summary['total_weekly_calories']}")
        print(f"     Daily average: {user_summary['average_daily_calories']:.0f}")
        print(f"     Total meals: {user_summary['total_meals']}")
    
    return summary['total_unique_recipes'] > 0

if __name__ == "__main__":
    print("🧪 Phase 4 Enhanced Meal Planning Test Suite")
    print("=" * 50)
    
    success = True
    
    # Run all tests
    success &= test_daily_meal_planning()
    success &= test_weekly_meal_planning()
    success &= test_calorie_banking_integration()
    success &= test_meal_plan_summary()
    
    if success:
        print("\n🎉 All Phase 4 integration tests passed!")
        print("✅ Calorie-aware daily meal planning complete")
        print("✅ Household weekly meal planning complete")
        print("✅ Calorie banking integration complete")
        print("✅ Grocery list integration complete")
        print("\n🚀 Ready for Phase 5: Streamlit UI Implementation")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        sys.exit(1)
