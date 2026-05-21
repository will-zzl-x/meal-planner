"""SQLite implementation of MealPlanRepository (migration 006)."""
import uuid
from datetime import date, datetime, timedelta
from typing import List

from core.interfaces.meal_plan_repository import IMealPlanRepository, MealPlanEntry
from repositories.sqlite.database import DatabaseManager, to_date


# Sort meals in this canonical day order in returned lists.
_MEAL_TYPE_ORDER = {"breakfast": 0, "lunch": 1, "dinner": 2, "snack": 3}


def _row_to_entry(row) -> MealPlanEntry:
    return MealPlanEntry(
        id=row['id'],
        recipe_id=row['recipe_id'],
        planned_date=to_date(row["planned_date"]),
        planned_servings=row['planned_servings'],
        meal_type=row['meal_type'],
        recipe_name=row['recipe_name'],
        calories_per_serving=row['calories_per_serving'],
    )


class SQLiteMealPlanRepository(IMealPlanRepository):

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()  # idempotent

    def save_entry(self,
                   household_id: str,
                   recipe_id: str,
                   planned_date: date,
                   planned_servings: int,
                   meal_type: str) -> MealPlanEntry:
        if meal_type not in _MEAL_TYPE_ORDER:
            raise ValueError(f"Invalid meal_type: {meal_type!r}")
        if planned_servings < 1:
            raise ValueError("planned_servings must be >= 1")

        entry_id = str(uuid.uuid4())
        with self.db_manager.get_connection() as conn:
            # Replace if (household, date, recipe, meal_type) already exists.
            existing = conn.execute(
                """
                SELECT id FROM meal_plans
                WHERE household_id = ? AND planned_date = ?
                  AND recipe_id = ? AND meal_type = ?
                """,
                (household_id, planned_date.isoformat(), recipe_id, meal_type),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE meal_plans SET planned_servings = ? WHERE id = ?",
                    (planned_servings, existing['id']),
                )
                entry_id = existing['id']
            else:
                conn.execute(
                    """
                    INSERT INTO meal_plans
                        (id, household_id, recipe_id, planned_date,
                         planned_servings, meal_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (entry_id, household_id, recipe_id,
                     planned_date.isoformat(), planned_servings, meal_type),
                )
            conn.commit()

            row = conn.execute(_SELECT_WITH_RECIPE_JOIN + " WHERE mp.id = ?", (entry_id,)).fetchone()
        return _row_to_entry(row)

    def find_by_week(self, household_id: str, week_start_date: date) -> List[MealPlanEntry]:
        week_end = week_start_date + timedelta(days=7)
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                _SELECT_WITH_RECIPE_JOIN +
                """
                WHERE mp.household_id = ?
                  AND mp.planned_date >= ?
                  AND mp.planned_date < ?
                """,
                (household_id, week_start_date.isoformat(), week_end.isoformat()),
            )
            entries = [_row_to_entry(r) for r in cursor.fetchall()]
        entries.sort(key=lambda e: (e.planned_date, _MEAL_TYPE_ORDER[e.meal_type]))
        return entries

    def find_by_date_range(self, household_id: str, start: date, end: date) -> List[MealPlanEntry]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                _SELECT_WITH_RECIPE_JOIN +
                """
                WHERE mp.household_id = ?
                  AND mp.planned_date >= ?
                  AND mp.planned_date <= ?
                """,
                (household_id, start.isoformat(), end.isoformat()),
            )
            entries = [_row_to_entry(r) for r in cursor.fetchall()]
        entries.sort(key=lambda e: (e.planned_date, _MEAL_TYPE_ORDER[e.meal_type]))
        return entries

    def find_by_date(self, household_id: str, day: date) -> List[MealPlanEntry]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                _SELECT_WITH_RECIPE_JOIN +
                """
                WHERE mp.household_id = ?
                  AND mp.planned_date = ?
                """,
                (household_id, day.isoformat()),
            )
            entries = [_row_to_entry(r) for r in cursor.fetchall()]
        entries.sort(key=lambda e: _MEAL_TYPE_ORDER[e.meal_type])
        return entries

    def delete_entry(self, entry_id: str, household_id: str) -> bool:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM meal_plans WHERE id = ? AND household_id = ?",
                (entry_id, household_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear_week(self, household_id: str, week_start_date: date) -> int:
        week_end = week_start_date + timedelta(days=7)
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM meal_plans
                WHERE household_id = ?
                  AND planned_date >= ?
                  AND planned_date < ?
                """,
                (household_id, week_start_date.isoformat(), week_end.isoformat()),
            )
            conn.commit()
            return cursor.rowcount


_SELECT_WITH_RECIPE_JOIN = """
    SELECT mp.id, mp.recipe_id, mp.planned_date, mp.planned_servings, mp.meal_type,
           r.name AS recipe_name, r.calories_per_serving AS calories_per_serving
    FROM meal_plans mp
    JOIN recipes r ON mp.recipe_id = r.id
"""
