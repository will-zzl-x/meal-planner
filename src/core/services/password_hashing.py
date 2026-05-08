"""
Password hashing for V1 multi-account auth.

Uses PBKDF2-SHA256 from the Python standard library (no extra dependencies).
Hashes are stored as a self-describing string of the form

    pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>

so the iteration count can be raised in the future without breaking users
already in the database (we just rehash on next successful login).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

# OWASP guidance (2024) for PBKDF2-SHA256 is at least 600,000 iterations.
DEFAULT_ITERATIONS = 600_000
SALT_BYTES = 16
HASH_BYTES = 32  # SHA-256 native digest size

_ALGORITHM = "pbkdf2_sha256"


def hash_password(plaintext: str, *, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Produce a self-describing PBKDF2-SHA256 hash of plaintext."""
    if not isinstance(plaintext, str) or plaintext == "":
        raise ValueError("Password must be a non-empty string")
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", plaintext.encode("utf-8"), salt, iterations, dklen=HASH_BYTES,
    )
    return f"{_ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(plaintext: str, stored_hash: str) -> bool:
    """Constant-time check that plaintext matches the stored hash.

    Returns False (rather than raising) on any malformed input so that callers
    can treat "wrong password" and "garbage hash" identically without leaking
    information through error messages.
    """
    if not isinstance(plaintext, str) or not isinstance(stored_hash, str):
        return False
    parts = stored_hash.split("$")
    if len(parts) != 4 or parts[0] != _ALGORITHM:
        return False
    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", plaintext.encode("utf-8"), salt, iterations, dklen=len(expected),
    )
    return hmac.compare_digest(actual, expected)
