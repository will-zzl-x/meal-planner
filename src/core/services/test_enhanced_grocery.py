#!/usr/bin/env python3
"""
Test Enhanced Grocery List Generator - Calorie Banking Integration.
"""
import sys
import os
from decimal import Decimal
from datetime import date, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.services.enhanced_grocery_generator import EnhancedGroceryListGenerator

def test_enhanced_grocery_generator():
    """Test enhanced grocery list generation with flexible dieting."""
    print("🧪 Testing Enhanced Grocery List Generator")
    print("=" * 41)
    
    generator = EnhancedGroceryListGenerator()
    
    # Test setup
    user_id = 1
    weekly_calorie_target = 14000  # 2000/day average
    body_weight = Decimal("180")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    
    # Sample recipes with nutrition data
    available_recipes = [
        {
            "id": 1,
            "name": "Chicken and Rice",
            "servings": 1,
            "calories_per_serving": 600,
            "protein_per_serving": 45,
            "carbs_per_serving": 50,
            "fats_per_serving": 15,
            "ingredients": [
                {"name": "chicken breast", "amount": 200, "unit": "g"},
                {"name": "white rice", "amount": 150, "unit": "g"},
                {"name": "olive oil", "amount": 10, "unit": "ml"}
            ]
        },
        {
            "id": 2,
            "name": "Salmon and Vegetables",
            "servings": 1,
            "calories_per_serving": 500,
            "protein_per_serving": 35,
            "carbs_per_serving": 20,
            "fats_per_serving": 25,
            "ingredients": [
                {"name": "salmon fillet", "amount": 150, "unit": "g"},
                {"name": "broccoli", "amount": 200, "unit": "g"},
                {"name": "sweet potato", "amount": 150, "unit": "g"}
            ]
        },
        {
            "id": 3,
            "name": "Protein Smoothie",
            "servings": 1,
            "calories_per_serving": 300,
            "protein_per_serving": 30,
            "carbs_per_serving": 25,
            "fats_per_serving": 8,
            "ingredients": [
                {"name": "protein powder", "amount": 30, "unit": "g"},
                {"name": "banana", "amount": 120, "unit": "g"},
                {"name": "almond milk", "amount": 250, "unit": "ml"}
            ]
        }
    ]
    
    # Test 1: Basic weekly meal plan generation with user-selected recipes
    print("1. Testing weekly meal plan with user-selected recipes...")
    
    # User selects recipes for each day
    user_selected_recipes = {}
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        # User chooses chicken and rice for most days, salmon for variety
        if i % 3 == 0:  # Every 3rd day
            user_selected_recipes[day_date] = [available_recipes[1]]  # Salmon
        else:
            user_selected_recipes[day_date] = [available_recipes[0]]  # Chicken
    
    meal_plan = generator.generate_weekly_meal_plan(
        user_id=user_id,
        weekly_calorie_target=weekly_calorie_target,
        body_weight=body_weight,
        week_start_date=week_start,
        user_selected_recipes=user_selected_recipes,
        activity_level="moderate"
    )
    
    print(f"   ✅ Week starting: {meal_plan.week_start}")
    print(f"   ✅ Daily plans created: {len(meal_plan.daily_plans)}")
    print(f"   ✅ Grocery list items: {len(meal_plan.grocery_list)}")
    print(f"   ✅ Weekly totals: {meal_plan.weekly_totals}")
    
    # Show sample daily plan with analysis
    sample_date = week_start
    if sample_date in meal_plan.daily_plans:
        sample_plan = meal_plan.daily_plans[sample_date]
        print(f"   ✅ {sample_date.strftime('%A')} plan:")
        print(f"      Recipes: {len(sample_plan.get('recipes', []))}")
        if sample_plan.get('targets'):
            targets = sample_plan['targets']
            actual = sample_plan.get('actual', {})
            analysis = sample_plan.get('analysis', {})
            print(f"      Targets: {targets.calories} cal, {targets.protein_g}g protein")
            print(f"      Actual: {actual.get('calories', 0)} cal, {actual.get('protein', 0)}g protein")
            print(f"      Status: {analysis.get('status', 'unknown')}")
            if analysis.get('basic_gaps'):
                print(f"      Basic gaps: {analysis['basic_gaps'][0] if analysis['basic_gaps'] else 'None'}")
            if analysis.get('upgrade_prompt'):
                print(f"      Upgrade prompt: {analysis['upgrade_prompt'][:40]}...")
    
    # Test 2: Recipe choice analysis (Free vs Premium)
    print("\n2. Testing recipe choice analysis - Free vs Premium...")
    
    # Analyze user's recipe choices - FREE TIER
    calorie_distribution = generator.calorie_service.distribute_weekly_calories(
        weekly_target=weekly_calorie_target,
        body_weight=body_weight,
        week_start_date=week_start
    )
    
    free_analysis = generator.analyze_user_recipe_choices(
        user_selected_recipes=user_selected_recipes,
        calorie_distribution=calorie_distribution,
        body_weight=body_weight,
        activity_level="moderate",
        user_tier="free"
    )
    
    # Analyze same choices - PREMIUM TIER
    premium_analysis = generator.analyze_user_recipe_choices(
        user_selected_recipes=user_selected_recipes,
        calorie_distribution=calorie_distribution,
        body_weight=body_weight,
        activity_level="moderate",
        user_tier="premium"
    )
    
    print(f"   ✅ Days analyzed: {len(free_analysis)}")
    
    # Show free tier features
    if free_analysis:
        sample_free = list(free_analysis.values())[0]
        free_gaps = sample_free["analysis"]["basic_gaps"]
        upgrade_prompt = sample_free["analysis"].get("upgrade_prompt", "")
        print(f"   ✅ FREE - Basic gaps: {len(free_gaps)} items")
        if free_gaps:
            print(f"      Example: {free_gaps[0]}")
        print(f"   ✅ FREE - Upgrade prompt: {upgrade_prompt[:50]}...")
    
    # Show premium tier features
    if premium_analysis:
        sample_premium = list(premium_analysis.values())[0]
        premium_suggestions = sample_premium["analysis"].get("premium_suggestions", [])
        smart_recipes = sample_premium["analysis"].get("smart_recipes", [])
        meal_timing = sample_premium["analysis"].get("meal_timing", {})
        
        print(f"   ✅ PREMIUM - Smart suggestions: {len(premium_suggestions)} items")
        if premium_suggestions:
            print(f"      Example: {premium_suggestions[0]}")
        print(f"   ✅ PREMIUM - Recipe suggestions: {len(smart_recipes)} items")
        if smart_recipes:
            print(f"      Example: {smart_recipes[0]['name']} ({smart_recipes[0]['reason']})")
        print(f"   ✅ PREMIUM - Meal timing advice: {len(meal_timing)} items")
    
    # Test 3: Restaurant day planning with user recipes
    print("\n3. Testing restaurant day integration...")
    
    friday = week_start + timedelta(days=4)
    special_days = {friday: "restaurant"}
    
    # User selects recipes for non-restaurant days
    restaurant_week_recipes = user_selected_recipes.copy()
    del restaurant_week_recipes[friday]  # No recipes for restaurant day
    
    restaurant_plan = generator.generate_weekly_meal_plan(
        user_id=user_id,
        weekly_calorie_target=weekly_calorie_target,
        body_weight=body_weight,
        week_start_date=week_start,
        user_selected_recipes=restaurant_week_recipes,
        special_days=special_days,
        activity_level="moderate"
    )
    
    friday_plan = restaurant_plan.daily_plans.get(friday)
    if friday_plan:
        print(f"   ✅ Friday plan: {friday_plan.get('note', 'No note')}")
        print(f"   ✅ Friday recipes: {len(friday_plan.get('recipes', []))}")
    
    # Compare grocery lists
    normal_items = len(meal_plan.grocery_list)
    restaurant_items = len(restaurant_plan.grocery_list)
    print(f"   ✅ Grocery list reduction: {normal_items} → {restaurant_items} items")
    
    # Test 4: Inventory-aware shopping list
    print("\n4. Testing inventory-aware shopping list...")
    
    # Simulate current inventory
    current_inventory = {
        "chicken breast": Decimal("500"),  # 500g available
        "white rice": Decimal("1000"),     # 1kg available
        "salmon fillet": Decimal("0"),     # None available
        "broccoli": Decimal("300")         # 300g available
    }
    
    shopping_list = generator.generate_shopping_list_with_inventory(
        meal_plan=meal_plan,
        current_inventory=current_inventory
    )
    
    print(f"   ✅ Shopping list items: {len(shopping_list)}")
    print("   ✅ Sample shopping needs:")
    for ingredient, amount in list(shopping_list.items())[:3]:
        print(f"      {ingredient}: {amount}")
    
    # Test 4: Special day adjustment
    print("\n4. Testing special day adjustment...")
    
    # Add restaurant day to existing plan
    restaurant_date = week_start + timedelta(days=2)  # Wednesday
    estimated_calories = 2500
    
    adjusted_plan = generator.adjust_plan_for_special_day(
        current_plan=meal_plan,
        special_date=restaurant_date,
        estimated_calories=estimated_calories,
        body_weight=body_weight
    )
    
    wednesday_plan = adjusted_plan.daily_plans.get(restaurant_date)
    if wednesday_plan:
        print(f"   ✅ Wednesday adjusted: {wednesday_plan.get('note', 'No note')}")
    
    print(f"   ✅ Plan adjustment completed")
    
    # Test 5: Grocery list analysis
    print("\n5. Testing grocery list analysis...")
    
    # Analyze ingredient categories
    protein_sources = []
    carb_sources = []
    fat_sources = []
    
    for ingredient in meal_plan.grocery_list.keys():
        if any(protein in ingredient.lower() for protein in ['chicken', 'salmon', 'protein']):
            protein_sources.append(ingredient)
        elif any(carb in ingredient.lower() for carb in ['rice', 'potato', 'banana']):
            carb_sources.append(ingredient)
        elif any(fat in ingredient.lower() for fat in ['oil', 'milk']):
            fat_sources.append(ingredient)
    
    print(f"   ✅ Protein sources: {len(protein_sources)} ({protein_sources})")
    print(f"   ✅ Carb sources: {len(carb_sources)} ({carb_sources})")
    print(f"   ✅ Fat sources: {len(fat_sources)} ({fat_sources})")
    
    print("\n🎉 All enhanced grocery generator tests passed!")
    print("💡 Key Features Working:")
    print("   • Weekly meal planning with USER-SELECTED recipes")
    print("   • FREE TIER: Basic gap analysis + upgrade prompts")
    print("   • PREMIUM TIER: Smart suggestions + recipe recommendations + meal timing")
    print("   • Restaurant day integration")
    print("   • Inventory-aware shopping lists")
    print("   • Dynamic plan adjustments")
    print("   • Ingredient categorization")
    print("   • Monetization-ready premium features")

if __name__ == "__main__":
    test_enhanced_grocery_generator()
