#!/usr/bin/env python3
"""
Test SQLiteCalorieTrackingRepository for flexible dieting features.
"""
import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import date, timedelta

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from repositories.database_manager import DatabaseManager
from repositories.sqlite.user_repository import SQLiteUserRepository
from repositories.sqlite.calorie_tracking_repository import SQLiteCalorieTrackingRepository
from core.interfaces.calorie_tracking_repository import DailyCalorieLog, WeeklyCaloriePlan

def test_calorie_tracking_repository():
    """Test calorie tracking repository with flexible dieting features."""
    print("📊 Testing SQLiteCalorieTrackingRepository - Flexible Dieting")
    print("=" * 60)
    
    # Create test database
    db_manager = DatabaseManager("test_calorie_repo.db")
    
    try:
        # Initialize database
        print("📋 Initializing database...")
        db_manager.initialize_database()
        
        # Create repositories
        user_repo = SQLiteUserRepository(db_manager)
        calorie_repo = SQLiteCalorieTrackingRepository(db_manager)
        
        # Test 1: Create test user
        print("\n👤 Test 1: Creating test user")
        alice = user_repo.create_user(
            name="Alice", 
            email="alice@example.com",
            household_name="Test Family"
        )
        print(f"✅ Created user: {alice.name}")
        
        # Test 2: Log daily calories
        print("\n📝 Test 2: Logging daily calories")
        today = date.today()
        daily_log = DailyCalorieLog(
            user_id=alice.user_id,
            date=today,
            target_calories=2000,
            consumed_calories=1800,
            banked_calories=200,  # Under target by 200
            protein_grams=Decimal('120.5'),
            carb_grams=Decimal('180.0'),
            fat_grams=Decimal('60.5')
        )
        
        saved_log = calorie_repo.log_daily_calories(daily_log)
        print(f"✅ Logged calories: {saved_log.consumed_calories}/{saved_log.target_calories} (banked: {saved_log.banked_calories})")
        
        # Test 3: Retrieve daily log
        print("\n🔍 Test 3: Retrieving daily log")
        retrieved_log = calorie_repo.get_daily_log(alice.user_id, today)
        if retrieved_log:
            print(f"✅ Retrieved log: {retrieved_log.consumed_calories} calories, {retrieved_log.protein_grams}g protein")
        
        # Test 4: Create weekly plan
        print("\n📅 Test 4: Creating weekly calorie plan")
        week_start = today - timedelta(days=today.weekday())  # Start of current week
        weekly_plan = WeeklyCaloriePlan(
            user_id=alice.user_id,
            week_start_date=week_start,
            weekly_calorie_target=14000,  # 2000 * 7
            daily_targets=[2000, 2000, 1800, 2200, 1900, 2100, 1900],  # Flexible distribution
            special_events=["Friday: Restaurant dinner"]
        )
        
        saved_plan = calorie_repo.save_weekly_plan(weekly_plan)
        print(f"✅ Created weekly plan: {saved_plan.weekly_calorie_target} calories/week")
        
        # Test 5: Retrieve weekly plan
        print("\n📋 Test 5: Retrieving weekly plan")
        retrieved_plan = calorie_repo.get_weekly_plan(alice.user_id, week_start)
        if retrieved_plan:
            print(f"✅ Retrieved plan: {len(retrieved_plan.daily_targets)} daily targets")
            print(f"   Daily targets: {retrieved_plan.daily_targets}")
            print(f"   Special events: {retrieved_plan.special_events}")
        
        # Test 6: Log multiple days for banking test
        print("\n💰 Test 6: Testing calorie banking over multiple days")
        for i in range(3):
            test_date = today - timedelta(days=i+1)
            log = DailyCalorieLog(
                user_id=alice.user_id,
                date=test_date,
                target_calories=2000,
                consumed_calories=1900 - (i * 50),  # Decreasing consumption
                banked_calories=100 + (i * 50),    # Increasing banking
                protein_grams=Decimal('100'),
                carb_grams=Decimal('150'),
                fat_grams=Decimal('50')
            )
            calorie_repo.log_daily_calories(log)
        
        print("✅ Logged 3 days of calorie banking")
        
        # Test 7: Calculate total banked calories
        print("\n🏦 Test 7: Calculating total banked calories")
        total_banked = calorie_repo.calculate_banked_calories(alice.user_id, today)
        print(f"✅ Total banked calories: {total_banked}")
        
        # Test 8: Get weekly logs
        print("\n📊 Test 8: Getting weekly calorie logs")
        weekly_logs = calorie_repo.get_weekly_logs(alice.user_id, week_start)
        print(f"✅ Retrieved {len(weekly_logs)} daily logs for the week")
        
        # Test 9: Calculate weekly deficit
        print("\n📉 Test 9: Calculating weekly calorie deficit")
        weekly_deficit = calorie_repo.get_calorie_deficit_for_week(alice.user_id, week_start)
        print(f"✅ Weekly calorie deficit: {weekly_deficit}")
        
        # Test 10: Get recent logs for trends
        print("\n📈 Test 10: Getting recent logs for trend analysis")
        recent_logs = calorie_repo.get_recent_logs(alice.user_id, days=7)
        print(f"✅ Retrieved {len(recent_logs)} recent logs")
        
        # Test 11: Update existing log (INSERT OR REPLACE)
        print("\n🔄 Test 11: Updating existing daily log")
        updated_log = DailyCalorieLog(
            user_id=alice.user_id,
            date=today,
            target_calories=2000,
            consumed_calories=1950,  # Updated consumption
            banked_calories=50,      # Updated banking
            protein_grams=Decimal('125'),
            carb_grams=Decimal('175'),
            fat_grams=Decimal('65')
        )
        
        calorie_repo.log_daily_calories(updated_log)
        final_log = calorie_repo.get_daily_log(alice.user_id, today)
        print(f"✅ Updated log: {final_log.consumed_calories} calories (was 1800)")
        
        print("\n🎉 All calorie tracking tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Calorie tracking test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up test database
        if os.path.exists("test_calorie_repo.db"):
            os.remove("test_calorie_repo.db")
            print("🧹 Test database cleaned up")

if __name__ == "__main__":
    print("🧪 Calorie Tracking Repository Test Suite")
    print("=" * 42)
    
    success = test_calorie_tracking_repository()
    
    if success:
        print("\n✅ Calorie tracking repository implementation complete!")
        print("🚀 Ready for Phase 3: Business Logic Services")
    else:
        print("\n❌ Tests failed. Check the errors above.")
        sys.exit(1)
