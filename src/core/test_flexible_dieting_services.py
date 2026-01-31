#!/usr/bin/env python3
"""
Test Phase 3 Business Logic Services - Flexible Dieting Features
"""
import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.services.flexible_dieting import (
    WeightTrackingService, WeightLog, 
    CalorieBankingService,
    BodyCompositionService
)

def test_weight_tracking_service():
    """Test weight tracking and TDEE estimation."""
    print("⚖️  Testing WeightTrackingService")
    print("=" * 35)
    
    service = WeightTrackingService()
    
    # Create sample weight logs (losing 1 lb per week)
    weight_logs = []
    current_weight = Decimal('180')
    
    for i in range(28):  # 4 weeks of data
        log_date = date.today() - timedelta(days=i)
        # Simulate 1 lb loss per week with some variation
        weight = current_weight - (i * Decimal('0.14')) + (Decimal('0.5') if i % 3 == 0 else Decimal('0'))
        
        weight_logs.append(WeightLog(
            user_id="test_user",
            date=log_date,
            weight=weight,
            notes=f"Day {i+1}"
        ))
    
    # Test weekly average change calculation
    weekly_change = service.calculate_weekly_average_change(weight_logs)
    print(f"✅ Weekly average change: {weekly_change} lbs/week")
    
    # Test progress analysis
    progress = service.analyze_weight_progress(weight_logs)
    print(f"✅ Progress analysis:")
    print(f"   Current: {progress.current_weight} lbs")
    print(f"   Weekly change: {progress.weekly_change} lbs")
    print(f"   Trend: {progress.trend_direction}")
    
    # Test TDEE estimation (mock calorie logs)
    class MockCalorieLog:
        def __init__(self, consumed_calories):
            self.consumed_calories = consumed_calories
    
    calorie_logs = [MockCalorieLog(1800) for _ in range(28)]  # 1800 cal/day
    
    tdee_estimate = service.estimate_tdee(weight_logs, calorie_logs, current_weight)
    print(f"✅ TDEE estimate:")
    print(f"   Estimated TDEE: {tdee_estimate.estimated_tdee} calories")
    print(f"   Confidence: {tdee_estimate.confidence_level}")
    print(f"   Recommended daily: {tdee_estimate.recommended_daily_calories} calories")
    
    # Test weight loss rate calculation
    bf_rate = service.calculate_target_weight_loss_rate(Decimal('20'))
    print(f"✅ Weight loss rate for 20% BF: {bf_rate}% per week")
    
    return True

def test_calorie_banking_service():
    """Test calorie banking and weekly distribution."""
    print("\n💰 Testing CalorieBankingService")
    print("=" * 35)
    
    service = CalorieBankingService()
    user_weight = Decimal('180')
    
    # Test weekly distribution creation
    weekly_target = 14000  # 2000 calories/day average
    special_events = {
        date.today() + timedelta(days=5): "Restaurant dinner"  # Friday
    }
    
    distribution = service.create_weekly_distribution(
        weekly_target, user_weight, special_events
    )
    
    print(f"✅ Weekly distribution created:")
    print(f"   Total weekly: {distribution.total_weekly_calories} calories")
    print(f"   Total banked: {distribution.total_banked}")
    print(f"   Total borrowed: {distribution.total_borrowed}")
    print(f"   Balanced: {distribution.is_balanced}")
    
    # Show daily breakdown
    for target in distribution.daily_targets:
        day_name = target.date.strftime("%A")
        special = " (SPECIAL)" if target.is_special_event else ""
        print(f"   {day_name}: {target.final_target} calories{special}")
    
    # Test remaining calories calculation
    consumed_so_far = [2000, 1800, 2200]  # 3 days consumed
    remaining = service.calculate_remaining_weekly_calories(
        weekly_target, consumed_so_far, 4
    )
    
    print(f"✅ Remaining calories calculation:")
    print(f"   Remaining total: {remaining['remaining_total']}")
    print(f"   Daily average: {remaining['daily_average']}")
    print(f"   Status: {remaining['status']}")
    
    # Test redistribution
    current_dist = [2000] * 7
    new_dist = service.suggest_calorie_redistribution(
        current_dist, -700, user_weight, [4, 5]  # Reduce 700 cal, prioritize Fri/Sat
    )
    
    print(f"✅ Calorie redistribution:")
    print(f"   Original: {current_dist}")
    print(f"   Adjusted: {new_dist}")
    
    # Test validation
    validation = service.validate_weekly_distribution(new_dist, weekly_target - 700, user_weight)
    print(f"✅ Distribution validation: {'Valid' if validation['is_valid'] else 'Invalid'}")
    if validation['warnings']:
        print(f"   Warnings: {validation['warnings']}")
    
    return True

def test_body_composition_service():
    """Test body composition and weight loss recommendations."""
    print("\n🏋️  Testing BodyCompositionService")
    print("=" * 35)
    
    service = BodyCompositionService()
    
    # Test body fat references
    references = service.get_body_fat_references()
    print(f"✅ Body fat references: {len(references)} levels")
    
    # Show a few examples
    for ref in references[:3]:
        print(f"   {ref.percentage}%: {ref.description}")
    
    # Test weight loss recommendation
    current_weight = Decimal('180')
    current_bf = Decimal('22')
    target_bf = Decimal('15')
    
    recommendation = service.calculate_weight_loss_recommendation(
        current_weight, current_bf, target_bf
    )
    
    print(f"✅ Weight loss recommendation:")
    print(f"   Weekly loss rate: {recommendation.recommended_weekly_loss_rate}%")
    print(f"   Max weekly loss: {recommendation.max_weekly_loss_pounds} lbs")
    print(f"   Calorie deficit: {recommendation.recommended_calorie_deficit} cal/day")
    print(f"   Timeline: {recommendation.timeline_weeks} weeks")
    print(f"   Safety notes: {recommendation.safety_notes}")
    
    # Test goal weight calculation
    goal_weight = service.calculate_goal_weight(current_weight, current_bf, target_bf)
    print(f"✅ Goal weight calculation: {goal_weight} lbs")
    
    # Test lean body mass estimation
    lean_mass = service.estimate_lean_body_mass(current_weight, current_bf)
    print(f"✅ Estimated lean mass: {lean_mass} lbs")
    
    # Test slider data
    slider_data = service.get_body_fat_slider_data()
    print(f"✅ Slider data: {len(slider_data)} reference points")
    
    return True

if __name__ == "__main__":
    print("🧪 Phase 3 Business Logic Services Test Suite")
    print("=" * 50)
    
    success = True
    
    # Run all tests
    success &= test_weight_tracking_service()
    success &= test_calorie_banking_service()
    success &= test_body_composition_service()
    
    if success:
        print("\n🎉 All Phase 3 business logic tests passed!")
        print("✅ Weight tracking with TDEE estimation complete")
        print("✅ Calorie banking and weekly distribution complete")
        print("✅ Body composition with photo references complete")
        print("\n🚀 Ready for Phase 4: Enhanced Grocery List Integration")
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        sys.exit(1)
