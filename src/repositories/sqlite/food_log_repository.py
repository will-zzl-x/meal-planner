"""SQLite implementation of FoodLogRepository (migration 007)."""
import uuid
from datetime import date, datetime
from typing import List

from core.interfaces.food_log_repository import FoodLogEntry, IFoodLogRepository
from repositories.sqlite.database import DatabaseManager


def _row_to_entry(row) -> FoodLogEntry:
    return FoodLogEntry(
        id=row['id'],
        user_id=row['user_id'],
        log_date=datetime.fromisoformat(row['log_date']).date(),
        calories=row['calories'],
        meal_plan_entry_id=row['meal_plan_entry_id'],
        description=row['description'],
    )


class SQLiteFoodLogRepository(IFoodLogRepository):

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()  # idempotent

    def log_planned_meal(self,
                         user_id: str,
                         meal_plan_entry_id: str,
                         log_date: date,
                         calories: int) -> FoodLogEntry:
        with self.db_manager.get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id, user_id, log_date, calories, meal_plan_entry_id, description
                FROM food_log_entries
                WHERE user_id = ? AND meal_plan_entry_id = ?
                """,
                (user_id, meal_plan_entry_id),
            ).fetchone()
            if existing:
                return _row_to_entry(existing)

            entry_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO food_log_entries
                    (id, user_id, log_date, meal_plan_entry_id, description, calories)
                VALUES (?, ?, ?, ?, NULL, ?)
                """,
                (entry_id, user_id, log_date.isoformat(), meal_plan_entry_id, calories),
            )
            conn.commit()
        return FoodLogEntry(
            id=entry_id,
            user_id=user_id,
            log_date=log_date,
            calories=calories,
            meal_plan_entry_id=meal_plan_entry_id,
            description=None,
        )

    def log_off_plan(self,
                     user_id: str,
                     log_date: date,
                     description: str,
                     calories: int) -> FoodLogEntry:
        if not description:
            raise ValueError("Off-plan log entries require a description")
        if calories < 0:
            raise ValueError("calories must be >= 0")

        entry_id = str(uuid.uuid4())
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO food_log_entries
                    (id, user_id, log_date, meal_plan_entry_id, description, calories)
                VALUES (?, ?, ?, NULL, ?, ?)
                """,
                (entry_id, user_id, log_date.isoformat(), description, calories),
            )
            conn.commit()
        return FoodLogEntry(
            id=entry_id,
            user_id=user_id,
            log_date=log_date,
            calories=calories,
            meal_plan_entry_id=None,
            description=description,
        )

    def find_by_date(self, user_id: str, log_date: date) -> List[FoodLogEntry]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, user_id, log_date, calories, meal_plan_entry_id, description
                FROM food_log_entries
                WHERE user_id = ? AND log_date = ?
                ORDER BY logged_at
                """,
                (user_id, log_date.isoformat()),
            )
            return [_row_to_entry(r) for r in cursor.fetchall()]

    def delete(self, entry_id: str, user_id: str) -> bool:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM food_log_entries WHERE id = ? AND user_id = ?",
                (entry_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
