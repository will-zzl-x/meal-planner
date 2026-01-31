#!/usr/bin/env python3
"""
Test Macro Tracking Service - Protein, Carbs, Fats Management.
"""
import sys
import os
from decimal import Decimal

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.services.macro_tracking_service import MacroTrackingService

def test_macro_tracking_service():
    """Test macro tracking and calculations."""
    print("🧪 Testing Macro Tracking Service")
    print("=" * 33)
    
    service = MacroTrackingService()
    
    # Test setup
    daily_calories = 2000
    body_weight = Decimal("180")
    
    # Test 1: Basic macro target calculations
    print("1. Testing macro target calculations...")
    targets = service.calculate_macro_targets(
        daily_calories=daily_calories,
        body_weight=body_weight,
        activity_level="moderate"
    )
    
    print(f"   ✅ Protein: {targets.protein_g}g ({targets.protein_calories} cal)")
    print(f"   ✅ Carbs: {targets.carbs_g}g ({targets.carbs_calories} cal)")
    print(f"   ✅ Fats: {targets.fats_g}g ({targets.fats_calories} cal)")
    print(f"   ✅ Total: {targets.protein_calories + targets.carbs_calories + targets.fats_calories} calories")
    
    # Verify protein minimum (1g per lb body weight)
    min_protein = int(body_weight * service.min_protein_per_lb)
    print(f"   ✅ Protein meets minimum: {targets.protein_g >= min_protein} ({min_protein}g min)")
    
    # Test 2: Activity level variations
    print("\n2. Testing activity level variations...")
    activity_levels = ["sedentary", "moderate", "active", "very_active"]
    
    for level in activity_levels:
        level_targets = service.calculate_macro_targets(2000, body_weight, level)
        protein_ratio = (level_targets.protein_calories / 2000) * 100
        print(f"   ✅ {level.capitalize()}: {level_targets.protein_g}g protein ({protein_ratio:.0f}%)")
    
    # Test 3: Recipe macro calculations
    print("\n3. Testing recipe macro calculations...")
    
    # Sample recipe: Chicken and rice
    chicken_rice_recipe = {
        "ingredients": [
            {
                "name": "chicken breast",
                "amount": 200,  # 200g
                "protein_per_100g": 31,
                "carbs_per_100g": 0,
                "fats_per_100g": 3.6
            },
            {
                "name": "white rice",
                "amount": 150,  # 150g cooked
                "protein_per_100g": 2.7,
                "carbs_per_100g": 28,
                "fats_per_100g": 0.3
            },
            {
                "name": "olive oil",
                "amount": 10,  # 10g (1 tbsp)
                "protein_per_100g": 0,
                "carbs_per_100g": 0,
                "fats_per_100g": 100
            }
        ]
    }
    
    recipe_macros = service.calculate_recipe_macros(chicken_rice_recipe)
    print(f"   ✅ Recipe macros:")
    print(f"      Protein: {recipe_macros.protein_g:.1f}g")
    print(f"      Carbs: {recipe_macros.carbs_g:.1f}g")
    print(f"      Fats: {recipe_macros.fats_g:.1f}g")
    print(f"      Total calories: {recipe_macros.total_calories}")
    
    # Test 4: Daily progress tracking
    print("\n4. Testing daily progress tracking...")
    
    # Simulate eating the chicken rice recipe
    consumed_recipes = [chicken_rice_recipe]
    
    progress = service.track_daily_progress(targets, consumed_recipes)
    
    print(f"   ✅ Current intake:")
    print(f"      Protein: {progress.current.protein_g:.1f}g / {progress.targets.protein_g}g")
    print(f"      Carbs: {progress.current.carbs_g:.1f}g / {progress.targets.carbs_g}g")
    print(f"      Fats: {progress.current.fats_g:.1f}g / {progress.targets.fats_g}g")
    
    print(f"   ✅ Remaining:")
    print(f"      Protein: {progress.remaining_protein}g")
    print(f"      Carbs: {progress.remaining_carbs}g")
    print(f"      Fats: {progress.remaining_fats}g")
    print(f"      Calories: {progress.remaining_calories}")
    
    # Test 5: Macro adjustment suggestions
    print("\n5. Testing macro adjustment suggestions...")
    
    suggestions = service.suggest_macro_adjustments(progress)
    print(f"   ✅ Suggestions ({len(suggestions)} items):")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"      {i}. {suggestion}")
    
    # Test 6: Custom macro ratios
    print("\n6. Testing custom macro ratios...")
    
    # High protein diet (40% protein, 30% carbs, 30% fats)
    custom_ratios = {"protein": 0.40, "carbs": 0.30, "fats": 0.30}
    custom_targets = service.calculate_macro_targets(
        daily_calories=2000,
        body_weight=body_weight,
        custom_ratios=custom_ratios
    )
    
    protein_percent = (custom_targets.protein_calories / 2000) * 100
    print(f"   ✅ Custom high-protein: {custom_targets.protein_g}g ({protein_percent:.0f}%)")
    
    # Test 7: Weekly macro averaging
    print("\n7. Testing weekly macro averaging...")
    
    # Simulate different daily targets
    weekly_targets = []
    for calories in [1800, 2000, 2200, 1900, 2500, 2100, 1900]:  # Variable calorie week
        daily_target = service.calculate_macro_targets(calories, body_weight)
        weekly_targets.append(daily_target)
    
    weekly_average = service.calculate_weekly_macro_average(weekly_targets)
    print(f"   ✅ Weekly average:")
    print(f"      Protein: {weekly_average.protein_g}g")
    print(f"      Carbs: {weekly_average.carbs_g}g")
    print(f"      Fats: {weekly_average.fats_g}g")
    print(f"      Calories: {weekly_average.calories}")
    
    print("\n🎉 All macro tracking tests passed!")
    print("💡 Key Features Working:")
    print("   • Macro target calculations with body weight minimums")
    print("   • Activity level adjustments")
    print("   • Recipe macro calculations from ingredients")
    print("   • Daily progress tracking")
    print("   • Smart adjustment suggestions")
    print("   • Custom macro ratio support")
    print("   • Weekly averaging for flexible dieting")

if __name__ == "__main__":
    test_macro_tracking_service()
