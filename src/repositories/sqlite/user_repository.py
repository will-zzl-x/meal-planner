"""
SQLite implementation of User Repository.

User profile fields (weight, body fat, calorie target) live directly on the
`users` table per migration 001 — there is no separate user_profiles table.
"""
import uuid
from decimal import Decimal
from typing import Optional

from core.interfaces.user_repository import IUserRepository, UserProfile
from repositories.sqlite.database import DatabaseManager


def _row_to_profile(row) -> UserProfile:
    """Map a SELECT * users row into a UserProfile."""
    return UserProfile(
        user_id=row['id'],
        name=row['name'],
        email=row['email'],
        current_weight=Decimal(str(row['current_weight'])) if row['current_weight'] is not None else None,
        body_fat_percentage=Decimal(str(row['body_fat_percentage'])) if row['body_fat_percentage'] is not None else None,
        target_weight_loss_per_week=Decimal(str(row['target_weight_loss_per_week'])) if row['target_weight_loss_per_week'] is not None else None,
        daily_calorie_target=row['daily_calorie_target'],
        household_id=row['household_id'],
        is_planner=bool(row['is_planner']),
        password_hash=row['password_hash'],
    )


_SELECT_COLUMNS = """
    id, name, email,
    current_weight, body_fat_percentage,
    target_weight_loss_per_week, daily_calorie_target,
    household_id, is_planner, password_hash
"""


class SQLiteUserRepository(IUserRepository):
    """SQLite implementation of user data access."""

    def __init__(self, db_path: str = "meal_planner.db"):
        self.db_manager = DatabaseManager(db_path)
        self.db_manager.initialize_database()  # idempotent

    def create_user(self,
                    name: str,
                    email: Optional[str] = None,
                    password_hash: Optional[str] = None,
                    household_id: Optional[str] = None,
                    is_planner: bool = False) -> UserProfile:
        user_id = str(uuid.uuid4())
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO users (id, name, email, password_hash, household_id, is_planner)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, name, email, password_hash, household_id, 1 if is_planner else 0),
            )
            conn.commit()
        return UserProfile(
            user_id=user_id,
            name=name,
            email=email,
            current_weight=None,
            body_fat_percentage=None,
            target_weight_loss_per_week=None,
            daily_calorie_target=None,
            household_id=household_id,
            is_planner=is_planner,
            password_hash=password_hash,
        )

    def find_by_id(self, user_id: str) -> Optional[UserProfile]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                f"SELECT {_SELECT_COLUMNS} FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return _row_to_profile(row) if row else None

    def find_by_email(self, email: str) -> Optional[UserProfile]:
        with self.db_manager.get_connection() as conn:
            row = conn.execute(
                f"SELECT {_SELECT_COLUMNS} FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        return _row_to_profile(row) if row else None

    def update_profile(self, user_profile: UserProfile) -> UserProfile:
        """Update profile data. Does NOT touch password_hash — use update_password_hash."""
        with self.db_manager.get_connection() as conn:
            conn.execute(
                """
                UPDATE users
                SET name = ?,
                    email = ?,
                    current_weight = ?,
                    body_fat_percentage = ?,
                    target_weight_loss_per_week = ?,
                    daily_calorie_target = ?,
                    household_id = ?,
                    is_planner = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    user_profile.name,
                    user_profile.email,
                    float(user_profile.current_weight) if user_profile.current_weight is not None else None,
                    float(user_profile.body_fat_percentage) if user_profile.body_fat_percentage is not None else None,
                    float(user_profile.target_weight_loss_per_week) if user_profile.target_weight_loss_per_week is not None else None,
                    user_profile.daily_calorie_target,
                    user_profile.household_id,
                    1 if user_profile.is_planner else 0,
                    user_profile.user_id,
                ),
            )
            conn.commit()
        return user_profile

    def update_password_hash(self, user_id: str, password_hash: str) -> bool:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (password_hash, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                return False
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return True
