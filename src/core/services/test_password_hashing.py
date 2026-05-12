"""
Tests for password_hashing. Iteration count is dialed down in the test calls
so the suite stays fast — production paths should always use the default.
"""
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.services.password_hashing import (
    DEFAULT_ITERATIONS,
    hash_password,
    verify_password,
)


_TEST_ITERATIONS = 1_000  # keeps the test suite snappy; not used in production.


def test_hash_then_verify_round_trip():
    h = hash_password("correct horse battery staple", iterations=_TEST_ITERATIONS)
    assert verify_password("correct horse battery staple", h) is True


def test_verify_rejects_wrong_password():
    h = hash_password("correct horse battery staple", iterations=_TEST_ITERATIONS)
    assert verify_password("wrong password", h) is False


def test_hashes_of_same_password_differ_due_to_salt():
    a = hash_password("same", iterations=_TEST_ITERATIONS)
    b = hash_password("same", iterations=_TEST_ITERATIONS)
    assert a != b
    # But each verifies against the same plaintext.
    assert verify_password("same", a) and verify_password("same", b)


def test_hash_format_is_self_describing():
    h = hash_password("anything", iterations=_TEST_ITERATIONS)
    parts = h.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) == _TEST_ITERATIONS
    # Salt + digest must be valid hex of expected length.
    assert len(parts[2]) == 32   # 16 bytes hex
    assert len(parts[3]) == 64   # 32 bytes hex


def test_default_iterations_is_owasp_floor():
    # Sanity guard against accidentally lowering the production default.
    assert DEFAULT_ITERATIONS >= 600_000


def test_verify_returns_false_for_malformed_hash():
    assert verify_password("x", "") is False
    assert verify_password("x", "not-a-hash") is False
    assert verify_password("x", "pbkdf2_sha256$abc$def") is False  # wrong segment count
    assert verify_password("x", "pbkdf2_sha256$notnumber$aa$bb") is False
    assert verify_password("x", "scrypt$1$aa$bb") is False  # different algorithm
    assert verify_password("x", "pbkdf2_sha256$1$zz$bb") is False  # bad hex


def test_verify_returns_false_for_non_string_inputs():
    h = hash_password("x", iterations=_TEST_ITERATIONS)
    assert verify_password(None, h) is False  # type: ignore[arg-type]
    assert verify_password("x", None) is False  # type: ignore[arg-type]


def test_empty_password_raises():
    with pytest.raises(ValueError):
        hash_password("")


def test_zero_iterations_raises():
    with pytest.raises(ValueError):
        hash_password("x", iterations=0)
