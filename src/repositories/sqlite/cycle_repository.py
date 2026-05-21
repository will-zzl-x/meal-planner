"""SQLite/Postgres implementation of ICycleRepository (migration 013)."""
import uuid
from datetime import date
from typing import List, Optional

from core.interfaces.cycle_repository import Cycle, ICycleRepository
from repositories.sqlite.database import DatabaseManager, to_date


def _row_to_cycle(row) -> Cycle:
    return Cycle(
        id=row['id'],
        household_id=row['household_id'],
        start_date=to_date(row['start_date']),
        end_date=to_date(row['end_date']),
        status=row['status'],
    )


class SQLiteCycleRepository(ICycleRepository):

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()

    def create(self, household_id: str, start_date: date, end_date: date) -> Cycle:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        cycle_id = str(uuid.uuid4())
        with self.db_manager.get_connection() as conn:
            conn.execute(
                "UPDATE cycles SET status = 'archived' "
                "WHERE household_id = ? AND status = 'active'",
                (household_id,),
            )
            conn.execute(
                """
                INSERT INTO cycles (id, household_id, start_date, end_date, status)
                VALUES (?, ?, ?, ?, 'active')
                """,
                (cycle_id, household_id,
                 start_date.isoformat(), end_date.isoformat()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM cycles WHERE id = ?", (cycle_id,)
            ).fetchone()
        return _row_to_cycle(row)

    def find_active(self, household_id: str) -> Optional[Cycle]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM cycles WHERE household_id = ? AND status = 'active'",
                (household_id,),
            ).fetchone()
        return _row_to_cycle(row) if row else None

    def find_all(self, household_id: str) -> List[Cycle]:
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM cycles WHERE household_id = ? ORDER BY start_date DESC",
                (household_id,),
            ).fetchall()
        return [_row_to_cycle(r) for r in rows]

    def archive(self, cycle_id: str, household_id: str) -> bool:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE cycles SET status = 'archived' WHERE id = ? AND household_id = ?",
                (cycle_id, household_id),
            )
            conn.commit()
        return cursor.rowcount > 0
