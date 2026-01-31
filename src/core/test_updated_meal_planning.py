#!/usr/bin/env python3
"""
Test Updated Meal Planning - Whole Meals & Comprehensive Grocery Lists
"""
import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import date

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.services.meal_planning_service import MealPlanningService, FoodItem
from core.domain.models import Recipe, Ingredient, InventoryItem

def test_whole_meal_coverage():
    """Test recipe meal coverage with whole meals only."""
    print("🍽️  Testing Whole Meal Coverage")
    print("=" * 35)
    
    service = MealPlanningService()
    
    # Create test recipe
    recipe = Recipe(
        name="Chicken Stir Fry",
        ingredients=[
            Ingredient("chicken_breast", Decimal('6'), "oz"),
            Ingredient("vegetables", Decimal('2'), "cup"),
        ],
        base_servings=2,
        calories_per_serving=400
    )
    
    # Test meal coverage calculation
    servings_made = Decimal('6')  # Making 6 servings
    target_calories = 600  # Want 600 calories per meal
    
    coverage = service.calculate_recipe_meal_coverage(recipe, servings_made, target_calories)
    
    print(f"✅ Recipe: {recipe.name}")
    print(f"   Servings made: {servings_made}")
    print(f"   Target calories per meal: {target_calories}")
    print(f"   Whole meals covered: {coverage['whole_meals_covered']}")
    print(f"   Days covered: {coverage['days_covered']}")
    print(f"   Servings per meal: {coverage['servings_per_meal']}")
    print(f"   Leftover servings: {coverage['leftover_servings']}")
    print(f"   Leftover calories: {coverage['leftover_calories']}")
    
    return coverage['whole_meals_covered'] == 4  # Should be 4 whole meals

def test_comprehensive_grocery_list():
    """Test grocery list including recipes and individual foods."""
    print("\n🛒 Testing Comprehensive Grocery List")
    print("=" * 40)
    
    service = MealPlanningService()
    
    # Create test recipe
    recipe = Recipe(
        name="Protein Bowl",
        ingredients=[
            Ingredient("chicken_breast", Decimal('6'), "oz"),
            Ingredient("rice", Decimal('1'), "cup"),
        ],
        base_servings=1,
        calories_per_serving=500
    )
    
    # Create meal plan entries
    recipe_entry = service.add_recipe_to_meal_plan(
        "user1", date.today(), "lunch", recipe, Decimal('2')
    )
    
    # Add individual food items
    almonds = service.search_food_database("almonds")[0]
    banana = service.search_food_database("banana")[0]
    
    almond_entry = service.add_food_item_to_meal_plan(
        "user1", date.today(), "snack", almonds, Decimal('2')  # 2 oz almonds
    )
    
    banana_entry = service.add_food_item_to_meal_plan(
        "user1", date.today(), "snack", banana, Decimal('1')  # 1 banana
    )
    
    # Create daily meal plan
    daily_plan = service.create_daily_meal_plan_from_entries(
        "user1", date.today(), 2000, [recipe_entry, almond_entry, banana_entry]
    )
    
    print(f"✅ Daily meal plan created:")
    print(f"   Total calories: {daily_plan.total_calories}")
    print(f"   Meals: {len(daily_plan.meals)}")
    
    for meal in daily_plan.meals:
        if meal.item_type == "recipe":
            print(f"   • {meal.meal_type}: {meal.recipe.name} ({meal.servings} servings)")
        else:
            print(f"   • {meal.meal_type}: {meal.food_item.name} ({meal.quantity} {meal.food_item.unit})")
    
    # Generate comprehensive grocery list
    inventory = [InventoryItem("rice", Decimal('0.5'), "cup")]  # Have some rice
    
    grocery_list = service.generate_comprehensive_grocery_list([daily_plan], inventory)
    
    print(f"\n✅ Comprehensive grocery list:")
    for item in grocery_list:
        print(f"   • {item.name}: {item.display_amount}")
    
    # Should include chicken (from recipe), almonds, and banana (individual foods)
    item_names = [item.name.lower() for item in grocery_list]
    has_recipe_ingredient = any("chicken" in name for name in item_names)
    has_individual_foods = any("almond" in name for name in item_names) and any("banana" in name for name in item_names)
    
    return has_recipe_ingredient and has_individual_foods

def test_food_database_search():
    """Test food database search functionality."""
    print("\n🔍 Testing Food Database Search")
    print("=" * 35)
    
    service = MealPlanningService()
    
    # Test search
    results = service.search_food_database("almond")
    print(f"✅ Search for 'almond': {len(results)} results")
    
    if results:
        almond = results[0]
        print(f"   • {almond.name}: {almond.calories_per_unit} cal/{almond.unit}")
        print(f"     Protein: {almond.protein_per_unit}g, Carbs: {almond.carbs_per_unit}g, Fat: {almond.fats_per_unit}g")
    
    # Test category search
    fruits = service.search_food_database("", category="fruit")
    print(f"✅ Fruit category: {len(fruits)} items")
    
    for fruit in fruits:
        print(f"   • {fruit.name}: {fruit.calories_per_unit} cal/{fruit.unit}")
    
    return len(results) > 0 and len(fruits) > 0

if __name__ == "__main__":
    print("🧪 Updated Meal Planning Test Suite")
    print("=" * 40)
    
    success = True
    
    # Run tests
    success &= test_whole_meal_coverage()
    success &= test_comprehensive_grocery_list()
    success &= test_food_database_search()
    
    if success:
        print("\n🎉 All updated meal planning tests passed!")
        print("✅ Whole meal coverage calculation working")
        print("✅ Comprehensive grocery lists including individual foods")
        print("✅ Food database search functionality working")
        print("\n🚀 Ready for Phase 5: Streamlit UI Implementation")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        sys.exit(1)
    
    # Notification sound attempt
    print("\n🔔 Attempting notification sound...")
    os.system('echo -e "\\a"')  # System bell
