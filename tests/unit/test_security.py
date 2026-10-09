"""Unit tests for app.shared.security helpers.

Covers password hashing / verification edge cases and JWT round-trips
for access vs refresh tokens. No DB, no docker, no network.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from jose import JWTError

from app.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_non_plaintext_hash() -> None:
    """hash_password returns a bcrypt-style string, not the plaintext."""
    hashed = hash_password("password123")
    assert hashed != "password123"
    assert hashed.startswith("$2")


def test_verify_password_correct_returns_true() -> None:
    """verify_password returns True for the matching plaintext."""
    hashed = hash_password("password123")
    assert verify_password("password123", hashed) is True


def test_verify_password_wrong_returns_false() -> None:
    """verify_password returns False for a non-matching plaintext."""
    hashed = hash_password("password123")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_with_malformed_hash_returns_false() -> None:
    """A malformed hash string must not raise — it returns False."""
    assert verify_password("anything", "not-a-valid-bcrypt-hash") is False


def test_access_token_roundtrip() -> None:
    """decode_access_token recovers sub/email/type from an access token."""
    user_id = uuid4()
    token = create_access_token(user_id, "alice@example.com")
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "alice@example.com"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload


def test_refresh_token_roundtrip() -> None:
    """decode_refresh_token recovers sub/email/type from a refresh token."""
    user_id = uuid4()
    token = create_refresh_token(user_id, "alice@example.com")
    payload = decode_refresh_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"


def test_decode_access_token_rejects_refresh_token() -> None:
    """decode_access_token must reject a token with type='refresh'."""
    refresh = create_refresh_token(uuid4(), "alice@example.com")
    with pytest.raises(JWTError):
        decode_access_token(refresh)


def test_decode_refresh_token_rejects_access_token() -> None:
    """decode_refresh_token must reject a token with type='access'."""
    access = create_access_token(uuid4(), "alice@example.com")
    with pytest.raises(JWTError):
        decode_refresh_token(access)
