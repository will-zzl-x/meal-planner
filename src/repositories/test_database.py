"""
Tests for the migration-based DatabaseManager — schema initialization,
foreign-key enforcement, and migration tracking.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from repositories.sqlite.database import DatabaseManager


def test_initialize_database_creates_core_tables(tmp_path):
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(str(db_path))

    manager.initialize_database()

    assert db_path.exists()
    with manager.get_connection() as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}

    # Tables created across migrations 001-005.
    for required in ("users", "recipes", "ingredients", "recipe_ingredients",
                     "households", "inventory", "weekly_calorie_plans",
                     "daily_calorie_logs", "weight_logs"):
        assert required in tables, f"missing table: {required}"


def test_initialize_database_is_idempotent(tmp_path):
    manager = DatabaseManager(str(tmp_path / "test.db"))
    manager.initialize_database()
    manager.initialize_database()  # second run must not raise

    applied = manager.get_applied_migrations()
    # Each migration should be recorded exactly once.
    assert len(applied) == len(set(applied))


def test_get_connection_enables_foreign_keys(tmp_path):
    manager = DatabaseManager(str(tmp_path / "test.db"))
    manager.initialize_database()

    with manager.get_connection() as conn:
        fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk_enabled == 1


def test_users_table_has_v1_auth_columns(tmp_path):
    manager = DatabaseManager(str(tmp_path / "test.db"))
    manager.initialize_database()

    with manager.get_connection() as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    assert "password_hash" in columns
    assert "is_planner" in columns
    assert "household_id" in columns
