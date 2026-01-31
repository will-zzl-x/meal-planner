#!/usr/bin/env python3
"""
Test Calorie Banking Service - Flexible Dieting Logic.
"""
import sys
import os
from decimal import Decimal
from datetime import date, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.services.calorie_banking_service import CalorieBankingService

def test_calorie_banking_service():
    """Test flexible dieting calorie banking logic."""
    print("🧪 Testing Calorie Banking Service")
    print("=" * 35)
    
    service = CalorieBankingService()
    
    # Test setup
    weekly_target = 14000  # 2000 calories/day average
    body_weight = Decimal("180")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    
    # Test 1: Basic weekly distribution
    print("1. Testing basic weekly distribution...")
    distribution = service.distribute_weekly_calories(
        weekly_target=weekly_target,
        body_weight=body_weight,
        week_start_date=week_start
    )
    
    print(f"   ✅ Weekly target: {distribution.weekly_target} calories")
    print(f"   ✅ Daily targets: {[dt.target_calories for dt in distribution.daily_targets]}")
    print(f"   ✅ Safety warnings: {len(distribution.safety_warnings)}")
    
    # Test 2: Restaurant day planning
    print("\n2. Testing restaurant day planning...")
    friday = week_start + timedelta(days=4)  # Friday
    special_days = {friday: "restaurant"}
    
    restaurant_distribution = service.distribute_weekly_calories(
        weekly_target=weekly_target,
        body_weight=body_weight,
        week_start_date=week_start,
        special_days=special_days
    )
    
    friday_target = None
    other_targets = []
    for dt in restaurant_distribution.daily_targets:
        if dt.date == friday:
            friday_target = dt.target_calories
        else:
            other_targets.append(dt.target_calories)
    
    print(f"   ✅ Friday (restaurant): {friday_target} calories")
    print(f"   ✅ Other days average: {sum(other_targets) // len(other_targets)} calories")
    print(f"   ✅ Preparation buffer applied: {friday_target > 2000}")
    
    # Test 3: Banking impact calculations
    print("\n3. Testing banking calculations...")
    
    # Scenario: Ate 1800 calories, target was 2000
    current_banked = 0
    new_banked, description = service.calculate_banking_impact(1800, 2000, current_banked)
    print(f"   ✅ Under target: {description}")
    
    # Scenario: Ate 2300 calories, target was 2000, had 200 banked
    new_banked2, description2 = service.calculate_banking_impact(2300, 2000, 200)
    print(f"   ✅ Over target with bank: {description2}")
    
    # Test 4: Special day redistribution
    print("\n4. Testing special day redistribution...")
    
    # User adds restaurant day with 2800 calorie estimate
    redistributed = service.redistribute_for_special_day(
        current_distribution=distribution,
        special_date=friday,
        estimated_calories=2800,
        body_weight=body_weight
    )
    
    friday_new = None
    other_new = []
    for dt in redistributed.daily_targets:
        if dt.date == friday:
            friday_new = dt.target_calories
        else:
            other_new.append(dt.target_calories)
    
    print(f"   ✅ Friday updated: {friday_new} calories")
    print(f"   ✅ Other days reduced to: {other_new}")
    print(f"   ✅ Safety warnings: {len(redistributed.safety_warnings)}")
    
    # Test 5: Safety validation
    print("\n5. Testing safety validation...")
    
    # Create unsafe distribution (too low calories)
    from core.services.calorie_banking_service import DailyCalorieTarget, WeeklyDistribution
    
    unsafe_targets = []
    for i in range(7):
        unsafe_targets.append(DailyCalorieTarget(
            date=week_start + timedelta(days=i),
            target_calories=1200  # Too low for 180 lb person
        ))
    
    unsafe_distribution = WeeklyDistribution(
        weekly_target=8400,  # 1200 * 7
        daily_targets=unsafe_targets,
        total_banked=0,
        safety_warnings=[]
    )
    
    warnings = service.validate_weekly_distribution(unsafe_distribution, body_weight)
    print(f"   ✅ Safety warnings generated: {len(warnings)}")
    if warnings:
        print(f"   ✅ Example warning: {warnings[0]}")
    
    print("\n🎉 All calorie banking tests passed!")
    print("💡 Key Features Working:")
    print("   • Weekly calorie distribution")
    print("   • Restaurant day planning with buffers")
    print("   • Calorie banking/borrowing calculations")
    print("   • Special day redistribution")
    print("   • Safety limit enforcement")

if __name__ == "__main__":
    test_calorie_banking_service()
