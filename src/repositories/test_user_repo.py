"""
Tests for SQLiteUserRepository — CRUD against the real schema.
"""
import sys
from pathlib import Path
from decimal import Decimal

sys.path.append(str(Path(__file__).parent.parent))

from repositories.sqlite.user_repository import SQLiteUserRepository


def _repo(tmp_path) -> SQLiteUserRepository:
    return SQLiteUserRepository(str(tmp_path / "users.db"))


def test_create_user_returns_profile_with_id_and_name(tmp_path):
    repo = _repo(tmp_path)
    user = repo.create_user("John Doe", "john@example.com")

    assert user.user_id
    assert user.name == "John Doe"
    assert user.email == "john@example.com"
    assert user.current_weight is None
    assert user.daily_calorie_target is None


def test_find_by_id_returns_persisted_user(tmp_path):
    repo = _repo(tmp_path)
    created = repo.create_user("Alice", "alice@example.com")

    found = repo.find_by_id(created.user_id)
    assert found is not None
    assert found.user_id == created.user_id
    assert found.name == "Alice"


def test_find_by_id_returns_none_for_missing(tmp_path):
    repo = _repo(tmp_path)
    assert repo.find_by_id("does-not-exist") is None


def test_find_by_email_returns_persisted_user(tmp_path):
    repo = _repo(tmp_path)
    created = repo.create_user("Alice", "alice@example.com")

    found = repo.find_by_email("alice@example.com")
    assert found is not None
    assert found.user_id == created.user_id


def test_update_profile_persists_weight_and_calorie_target(tmp_path):
    repo = _repo(tmp_path)
    user = repo.create_user("Bob")

    user.current_weight = Decimal("180.5")
    user.body_fat_percentage = Decimal("15.0")
    user.daily_calorie_target = 2000
    repo.update_profile(user)

    reloaded = repo.find_by_id(user.user_id)
    assert reloaded.current_weight == Decimal("180.5")
    assert reloaded.body_fat_percentage == Decimal("15.0")
    assert reloaded.daily_calorie_target == 2000


def test_delete_user_removes_record(tmp_path):
    repo = _repo(tmp_path)
    user = repo.create_user("ToDelete")

    assert repo.delete_user(user.user_id) is True
    assert repo.find_by_id(user.user_id) is None


def test_delete_user_returns_false_for_missing(tmp_path):
    repo = _repo(tmp_path)
    assert repo.delete_user("does-not-exist") is False
