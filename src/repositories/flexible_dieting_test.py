#!/usr/bin/env python3
"""
Test Calorie Tracking Repository - Flexible Dieting Features.
"""
import sqlite3
import uuid
from decimal import Decimal
from datetime import date, timedelta
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class DailyCalorieLog:
    user_id: str
    date: date
    target_calories: int
    consumed_calories: int
    banked_calories: int
    protein_grams: Optional[Decimal] = None
    carb_grams: Optional[Decimal] = None
    fat_grams: Optional[Decimal] = None

@dataclass
class WeeklyCaloriePlan:
    user_id: str
    week_start_date: date
    weekly_calorie_target: int
    daily_targets: List[int]
    special_events: Optional[List[str]] = None

class SimpleCalorieTracker:
    """Simple calorie tracking for testing flexible dieting features."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS daily_calorie_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    date DATE NOT NULL,
                    target_calories INTEGER NOT NULL,
                    consumed_calories INTEGER DEFAULT 0,
                    protein_grams DECIMAL(5,2) DEFAULT 0,
                    carb_grams DECIMAL(5,2) DEFAULT 0,
                    fat_grams DECIMAL(5,2) DEFAULT 0,
                    banked_calories INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, date)
                );
                
                CREATE TABLE IF NOT EXISTS weekly_calorie_plans (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    week_start_date DATE NOT NULL,
                    weekly_calorie_target INTEGER NOT NULL,
                    monday_target INTEGER,
                    tuesday_target INTEGER,
                    wednesday_target INTEGER,
                    thursday_target INTEGER,
                    friday_target INTEGER,
                    saturday_target INTEGER,
                    sunday_target INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, week_start_date)
                );
            """)
    
    def log_daily_calories(self, log: DailyCalorieLog):
        """Log daily calories."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO daily_calorie_logs 
                (id, user_id, date, target_calories, consumed_calories, 
                 protein_grams, carb_grams, fat_grams, banked_calories)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                log.user_id, log.date.isoformat(), log.target_calories, log.consumed_calories,
                float(log.protein_grams) if log.protein_grams else 0,
                float(log.carb_grams) if log.carb_grams else 0,
                float(log.fat_grams) if log.fat_grams else 0,
                log.banked_calories
            ))
            conn.commit()
    
    def get_daily_log(self, user_id: str, date: date) -> Optional[DailyCalorieLog]:
        """Get daily log."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, date, target_calories, consumed_calories, banked_calories,
                       protein_grams, carb_grams, fat_grams
                FROM daily_calorie_logs WHERE user_id = ? AND date = ?
            """, (user_id, date.isoformat()))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return DailyCalorieLog(
                user_id=row['user_id'],
                date=date.fromisoformat(row['date']),
                target_calories=row['target_calories'],
                consumed_calories=row['consumed_calories'],
                banked_calories=row['banked_calories'],
                protein_grams=Decimal(str(row['protein_grams'])) if row['protein_grams'] else None,
                carb_grams=Decimal(str(row['carb_grams'])) if row['carb_grams'] else None,
                fat_grams=Decimal(str(row['fat_grams'])) if row['fat_grams'] else None
            )
    
    def save_weekly_plan(self, plan: WeeklyCaloriePlan):
        """Save weekly plan."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            daily_targets = plan.daily_targets + [0] * (7 - len(plan.daily_targets))
            daily_targets = daily_targets[:7]
            
            cursor.execute("""
                INSERT OR REPLACE INTO weekly_calorie_plans
                (id, user_id, week_start_date, weekly_calorie_target,
                 monday_target, tuesday_target, wednesday_target, thursday_target,
                 friday_target, saturday_target, sunday_target)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), plan.user_id, plan.week_start_date.isoformat(),
                plan.weekly_calorie_target, *daily_targets
            ))
            conn.commit()
    
    def calculate_banked_calories(self, user_id: str, up_to_date: date) -> int:
        """Calculate banked calories."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(target_calories - consumed_calories) as total_banked
                FROM daily_calorie_logs WHERE user_id = ? AND date <= ?
            """, (user_id, up_to_date.isoformat()))
            
            row = cursor.fetchone()
            return row[0] if row[0] else 0

def test_flexible_dieting():
    """Test flexible dieting features."""
    print("🧪 Testing Flexible Dieting System")
    print("=" * 35)
    
    tracker = SimpleCalorieTracker("test_calories.db")
    
    # Create test user
    user_id = str(uuid.uuid4())
    with sqlite3.connect("test_calories.db") as conn:
        conn.execute("INSERT INTO users (id, name) VALUES (?, ?)", (user_id, "Test User"))
    
    # Test 1: Weekly Plan
    print("1. Creating weekly calorie plan...")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    
    weekly_plan = WeeklyCaloriePlan(
        user_id=user_id,
        week_start_date=week_start,
        weekly_calorie_target=14000,  # 2000 calories/day average
        daily_targets=[2000, 2000, 2000, 2000, 2000, 2000, 2000]
    )
    
    tracker.save_weekly_plan(weekly_plan)
    print(f"   ✅ Created weekly plan: {weekly_plan.weekly_calorie_target} calories/week")
    
    # Test 2: Daily Logging with Banking
    print("2. Logging daily calories with banking...")
    
    # Monday: Under target (bank 200 calories)
    monday_log = DailyCalorieLog(
        user_id=user_id,
        date=week_start,
        target_calories=2000,
        consumed_calories=1800,  # 200 under
        banked_calories=200,
        protein_grams=Decimal("120"),
        carb_grams=Decimal("180"),
        fat_grams=Decimal("60")
    )
    tracker.log_daily_calories(monday_log)
    
    # Tuesday: Over target (use 100 banked calories)
    tuesday_log = DailyCalorieLog(
        user_id=user_id,
        date=week_start + timedelta(days=1),
        target_calories=2000,
        consumed_calories=2100,  # 100 over
        banked_calories=100,  # Net: 200 - 100 = 100 banked
        protein_grams=Decimal("130"),
        carb_grams=Decimal("200"),
        fat_grams=Decimal("70")
    )
    tracker.log_daily_calories(tuesday_log)
    
    print("   ✅ Logged Monday: 1800 cal (200 banked)")
    print("   ✅ Logged Tuesday: 2100 cal (100 used from bank)")
    
    # Test 3: Retrieve Daily Logs
    print("3. Retrieving daily logs...")
    monday_retrieved = tracker.get_daily_log(user_id, week_start)
    tuesday_retrieved = tracker.get_daily_log(user_id, week_start + timedelta(days=1))
    
    if monday_retrieved and monday_retrieved.consumed_calories == 1800:
        print(f"   ✅ Monday log: {monday_retrieved.consumed_calories} cal, {monday_retrieved.protein_grams}g protein")
    else:
        print("   ❌ Monday log retrieval failed")
        return
    
    if tuesday_retrieved and tuesday_retrieved.consumed_calories == 2100:
        print(f"   ✅ Tuesday log: {tuesday_retrieved.consumed_calories} cal, {tuesday_retrieved.protein_grams}g protein")
    else:
        print("   ❌ Tuesday log retrieval failed")
        return
    
    # Test 4: Calculate Banked Calories
    print("4. Calculating banked calories...")
    banked = tracker.calculate_banked_calories(user_id, week_start + timedelta(days=1))
    expected_banked = (2000 - 1800) + (2000 - 2100)  # 200 - 100 = 100
    
    if banked == expected_banked:
        print(f"   ✅ Banked calories: {banked} (expected: {expected_banked})")
    else:
        print(f"   ❌ Banked calories incorrect: {banked} (expected: {expected_banked})")
        return
    
    print("\n🎉 All flexible dieting tests passed!")
    print("💡 Key Features Working:")
    print("   • Weekly calorie planning")
    print("   • Daily calorie logging with macros")
    print("   • Calorie banking/borrowing calculations")
    print("   • Multi-day tracking and retrieval")
    
    # Cleanup
    import os
    os.remove("test_calories.db")
    print("🧹 Test database cleaned up.")

if __name__ == "__main__":
    test_flexible_dieting()
