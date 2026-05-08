"""
Tests for DatabaseManager — schema initialization and connection setup.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from repositories.database_manager import DatabaseManager


def test_initialize_database_creates_schema(tmp_path):
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(str(db_path))

    assert manager.initialize_database() is True
    assert db_path.exists()

    with manager.get_connection() as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}

    # Schema should at least define the core tables the rest of the app uses.
    assert "users" in tables
    assert "recipes" in tables
    assert "ingredients" in tables


def test_get_connection_enables_foreign_keys(tmp_path):
    manager = DatabaseManager(str(tmp_path / "test.db"))
    manager.initialize_database()

    with manager.get_connection() as conn:
        fk_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]

    assert fk_enabled == 1


def test_check_database_exists_returns_false_for_missing_file(tmp_path):
    manager = DatabaseManager(str(tmp_path / "missing.db"))
    assert manager.check_database_exists() is False


def test_check_database_exists_returns_true_after_init(tmp_path):
    manager = DatabaseManager(str(tmp_path / "test.db"))
    manager.initialize_database()
    assert manager.check_database_exists() is True
