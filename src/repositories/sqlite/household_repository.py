"""
SQLite implementation of Household Repository.
"""
import uuid
from typing import List, Optional

from core.interfaces.household_repository import IHouseholdRepository, Household
from repositories.sqlite.database import DatabaseManager


class SQLiteHouseholdRepository(IHouseholdRepository):
    """SQLite implementation of household data access."""

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()  # idempotent: migrations track applied versions

    def create(self, name: str) -> Household:
        household_id = str(uuid.uuid4())
        with self.db_manager.get_connection() as conn:
            conn.execute(
                "INSERT INTO households (id, name) VALUES (?, ?)",
                (household_id, name),
            )
            conn.commit()
        return Household(id=household_id, name=name)

    def find_by_id(self, household_id: str) -> Optional[Household]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                "SELECT id, name FROM households WHERE id = ?",
                (household_id,),
            ).fetchone()
        if not row:
            return None
        return Household(id=row['id'], name=row['name'])

    def list_member_ids(self, household_id: str) -> List[str]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM users WHERE household_id = ? ORDER BY created_at",
                (household_id,),
            )
            return [row['id'] for row in cursor.fetchall()]
