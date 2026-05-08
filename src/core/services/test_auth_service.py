"""Tests for AuthService — register and login flows against real repositories."""
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    HouseholdNotFoundError,
)
from repositories.sqlite.household_repository import SQLiteHouseholdRepository
from repositories.sqlite.user_repository import SQLiteUserRepository


# Lower iteration count keeps the test suite fast; production uses the default.
_FAST_ITERATIONS = 1_000


def _service(tmp_path) -> AuthService:
    db = str(tmp_path / "auth.db")
    return AuthService(
        user_repo=SQLiteUserRepository(db),
        household_repo=SQLiteHouseholdRepository(db),
        hash_iterations=_FAST_ITERATIONS,
    )


def test_register_household_creates_household_and_planner(tmp_path):
    svc = _service(tmp_path)
    result = svc.register_household("Alice", "alice@example.com", "pw", "The Smiths")

    assert result.household.id
    assert result.household.name == "The Smiths"
    assert result.user.name == "Alice"
    assert result.user.email == "alice@example.com"
    assert result.user.household_id == result.household.id
    assert result.user.is_planner is True
    # Hash is stored, plaintext is never persisted.
    assert result.user.password_hash is not None
    assert "pw" not in result.user.password_hash


def test_register_household_rejects_duplicate_email(tmp_path):
    svc = _service(tmp_path)
    svc.register_household("Alice", "alice@example.com", "pw", "Smiths")
    with pytest.raises(EmailAlreadyRegisteredError):
        svc.register_household("Alice2", "alice@example.com", "pw", "Other")


def test_register_member_joins_existing_household(tmp_path):
    svc = _service(tmp_path)
    h = svc.register_household("Alice", "alice@example.com", "pw", "Smiths").household

    bob = svc.register_member("Bob", "bob@example.com", "pw", h.id)
    assert bob.household_id == h.id
    assert bob.is_planner is False


def test_register_member_rejects_unknown_household(tmp_path):
    svc = _service(tmp_path)
    with pytest.raises(HouseholdNotFoundError):
        svc.register_member("Bob", "bob@example.com", "pw", "no-such-household")


def test_register_member_rejects_duplicate_email(tmp_path):
    svc = _service(tmp_path)
    h = svc.register_household("Alice", "alice@example.com", "pw", "Smiths").household
    svc.register_member("Bob", "bob@example.com", "pw", h.id)
    with pytest.raises(EmailAlreadyRegisteredError):
        svc.register_member("Bob2", "bob@example.com", "pw", h.id)


def test_login_succeeds_with_correct_password(tmp_path):
    svc = _service(tmp_path)
    svc.register_household("Alice", "alice@example.com", "secret", "Smiths")

    user = svc.login("alice@example.com", "secret")
    assert user is not None
    assert user.email == "alice@example.com"


def test_login_fails_with_wrong_password(tmp_path):
    svc = _service(tmp_path)
    svc.register_household("Alice", "alice@example.com", "secret", "Smiths")

    assert svc.login("alice@example.com", "wrong") is None


def test_login_fails_for_unknown_email(tmp_path):
    svc = _service(tmp_path)
    assert svc.login("nobody@example.com", "anything") is None


def test_login_fails_for_user_without_password_hash(tmp_path):
    """A user row created without a password (legacy path) must not be loginable."""
    svc = _service(tmp_path)
    h = svc.household_repo.create("Smiths")
    svc.user_repo.create_user(name="Legacy", email="legacy@example.com", household_id=h.id)

    assert svc.login("legacy@example.com", "anything") is None
