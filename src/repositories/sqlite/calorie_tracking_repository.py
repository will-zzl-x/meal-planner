"""
SQLite implementation of Calorie Tracking Repository.
Handles daily logs, weekly plans, and calorie banking for flexible dieting.
"""
import sqlite3
import uuid
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from core.interfaces.calorie_tracking_repository import ICalorieTrackingRepository, DailyCalorieLog, WeeklyCaloriePlan
from repositories.sqlite.database import DatabaseManager

class SQLiteCalorieTrackingRepository(ICalorieTrackingRepository):
    """SQLite implementation of calorie tracking data access."""

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()  # idempotent
    
    def log_daily_calories(self, log: DailyCalorieLog) -> DailyCalorieLog:
        """Log daily calorie consumption with banking."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert or update daily log
            cursor.execute("""
                INSERT OR REPLACE INTO daily_calorie_logs 
                (id, user_id, date, target_calories, consumed_calories, 
                 protein_grams, carb_grams, fat_grams, banked_calories)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                log.user_id,
                log.date.isoformat(),
                log.target_calories,
                log.consumed_calories,
                float(log.protein_grams) if log.protein_grams else 0,
                float(log.carb_grams) if log.carb_grams else 0,
                float(log.fat_grams) if log.fat_grams else 0,
                log.banked_calories
            ))
            
            conn.commit()
        
        return log
    
    def get_daily_log(self, user_id: str, date: date) -> Optional[DailyCalorieLog]:
        """Get calorie log for a specific date."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, date, target_calories, consumed_calories,
                       protein_grams, carb_grams, fat_grams, banked_calories
                FROM daily_calorie_logs
                WHERE user_id = ? AND date = ?
            """, (user_id, date.isoformat()))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return DailyCalorieLog(
                user_id=row['user_id'],
                date=datetime.fromisoformat(row['date']).date(),
                target_calories=row['target_calories'],
                consumed_calories=row['consumed_calories'],
                banked_calories=row['banked_calories'],
                protein_grams=Decimal(str(row['protein_grams'])) if row['protein_grams'] else None,
                carb_grams=Decimal(str(row['carb_grams'])) if row['carb_grams'] else None,
                fat_grams=Decimal(str(row['fat_grams'])) if row['fat_grams'] else None
            )
    
    def get_weekly_logs(self, user_id: str, week_start_date: date) -> List[DailyCalorieLog]:
        """Get calorie logs for a week."""
        week_end_date = week_start_date + timedelta(days=6)
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, date, target_calories, consumed_calories,
                       protein_grams, carb_grams, fat_grams, banked_calories
                FROM daily_calorie_logs
                WHERE user_id = ? AND date BETWEEN ? AND ?
                ORDER BY date
            """, (user_id, week_start_date.isoformat(), week_end_date.isoformat()))
            
            logs = []
            for row in cursor.fetchall():
                logs.append(DailyCalorieLog(
                    user_id=row['user_id'],
                    date=datetime.fromisoformat(row['date']).date(),
                    target_calories=row['target_calories'],
                    consumed_calories=row['consumed_calories'],
                    banked_calories=row['banked_calories'],
                    protein_grams=Decimal(str(row['protein_grams'])) if row['protein_grams'] else None,
                    carb_grams=Decimal(str(row['carb_grams'])) if row['carb_grams'] else None,
                    fat_grams=Decimal(str(row['fat_grams'])) if row['fat_grams'] else None
                ))
            
            return logs
    
    def save_weekly_plan(self, plan: WeeklyCaloriePlan) -> WeeklyCaloriePlan:
        """Save weekly calorie distribution plan."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Ensure we have 7 daily targets
            daily_targets = plan.daily_targets + [0] * (7 - len(plan.daily_targets))
            daily_targets = daily_targets[:7]  # Limit to 7 days
            
            cursor.execute("""
                INSERT OR REPLACE INTO weekly_calorie_plans
                (id, user_id, week_start_date, weekly_calorie_target,
                 monday_target, tuesday_target, wednesday_target, thursday_target,
                 friday_target, saturday_target, sunday_target)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                plan.user_id,
                plan.week_start_date.isoformat(),
                plan.weekly_calorie_target,
                daily_targets[0], daily_targets[1], daily_targets[2], daily_targets[3],
                daily_targets[4], daily_targets[5], daily_targets[6]
            ))
            
            conn.commit()
        
        return plan
    
    def get_weekly_plan(self, user_id: str, week_start_date: date) -> Optional[WeeklyCaloriePlan]:
        """Get weekly calorie plan."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, week_start_date, weekly_calorie_target,
                       monday_target, tuesday_target, wednesday_target, thursday_target,
                       friday_target, saturday_target, sunday_target
                FROM weekly_calorie_plans
                WHERE user_id = ? AND week_start_date = ?
            """, (user_id, week_start_date.isoformat()))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            daily_targets = [
                row['monday_target'], row['tuesday_target'], row['wednesday_target'],
                row['thursday_target'], row['friday_target'], row['saturday_target'],
                row['sunday_target']
            ]
            
            return WeeklyCaloriePlan(
                user_id=row['user_id'],
                week_start_date=datetime.fromisoformat(row['week_start_date']).date(),
                weekly_calorie_target=row['weekly_calorie_target'],
                daily_targets=daily_targets,
                special_events=None  # TODO: Implement special events
            )
    
    def calculate_banked_calories(self, user_id: str, up_to_date: date) -> Decimal:
        """Calculate total banked calories up to a specific date."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT SUM(target_calories - consumed_calories) as total_banked
                FROM daily_calorie_logs
                WHERE user_id = ? AND date <= ?
            """, (user_id, up_to_date.isoformat()))
            
            row = cursor.fetchone()
            total_banked = row['total_banked'] if row['total_banked'] else 0
            
            return Decimal(str(total_banked))
