"""End-to-end API tests for the auth flow.

All tests use ``auth_client``, which wires the real UserUsecase + real
bcrypt/jose, but with in-memory repositories — no DB required.
"""
from __future__ import annotations

import pytest

from app.config.settings import settings

API = "/api/v1/users"

_CREDS = {
    "email": "alice@example.com",
    "username": "alice",
    "password": "password123",
}


@pytest.fixture
async def registered(auth_client):
    """Register the standard test user via the API."""
    r = await auth_client.post(f"{API}/register", json=_CREDS)
    assert r.status_code == 201, r.text
    return _CREDS


@pytest.fixture
async def tokens(auth_client, registered) -> dict:
    """Login and return the token payload."""
    r = await auth_client.post(
        f"{API}/login",
        json={"email": registered["email"], "password": registered["password"]},
    )
    assert r.status_code == 200, r.text
    return r.json()


async def test_register_returns_201(auth_client, user_repo):
    """POST /register creates a user and hides the password hash."""
    r = await auth_client.post(f"{API}/register", json=_CREDS)

    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["username"] == "alice"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert "password" not in body
    assert "hashed_password" not in body
    assert len(user_repo.users) == 1
    assert user_repo.users[0].hashed_password != "password123"


async def test_register_duplicate_email_returns_409(auth_client, registered):
    """Second register with the same email returns 409 Conflict."""
    r = await auth_client.post(
        f"{API}/register",
        json={**_CREDS, "username": "alice-2"},
    )
    assert r.status_code == 409
    assert "email" in r.json()["detail"].lower()


async def test_login_returns_tokens(auth_client, registered):
    """POST /login returns access_token, refresh_token, expires_in."""
    r = await auth_client.post(
        f"{API}/login",
        json={"email": _CREDS["email"], "password": _CREDS["password"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert isinstance(body["refresh_token"], str) and body["refresh_token"]


async def test_me_with_access_token_returns_200(auth_client, tokens):
    """GET /me with a valid access token returns the current user."""
    r = await auth_client.get(
        f"{API}/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == _CREDS["email"]


async def test_me_with_refresh_token_returns_401(auth_client, tokens):
    """GET /me rejects a refresh token (type mismatch)."""
    r = await auth_client.get(
        f"{API}/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert r.status_code == 401


async def test_me_without_token_returns_401(auth_client):
    """GET /me without Authorization header returns 401."""
    r = await auth_client.get(f"{API}/me")
    assert r.status_code == 401


async def test_refresh_token_returns_new_access(auth_client, tokens):
    """POST /refresh-token exchanges a valid refresh for a fresh access token."""
    r = await auth_client.post(
        f"{API}/refresh-token",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert isinstance(body["access_token"], str) and body["access_token"]

    me = await auth_client.get(
        f"{API}/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200


async def test_logout_returns_200(auth_client, tokens, blacklist_repo):
    """POST /logout blacklists the refresh token supplied via Bearer header."""
    assert len(blacklist_repo.entries) == 0

    r = await auth_client.post(
        f"{API}/logout",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert r.status_code == 200
    assert r.json() == {"message": "Logged out successfully"}
    assert len(blacklist_repo.entries) == 1


async def test_refresh_token_after_logout_returns_401(auth_client, tokens):
    """A refresh token that was just blacklisted cannot be reused."""
    logout = await auth_client.post(
        f"{API}/logout",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert logout.status_code == 200

    r = await auth_client.post(
        f"{API}/refresh-token",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# 10-12. Error branches in user_router
# ---------------------------------------------------------------------------


async def test_refresh_token_invalid_returns_401(auth_client):
    """POST /refresh-token with a garbage token → 401."""
    r = await auth_client.post(
        f"{API}/refresh-token",
        json={"refresh_token": "this-is-not-a-valid-jwt-token-at-all"},
    )
    assert r.status_code == 401


async def test_logout_invalid_token_returns_401(auth_client):
    """POST /logout with a garbage bearer token → 401."""
    r = await auth_client.post(
        f"{API}/logout",
        headers={
            "Authorization": "Bearer this-is-not-a-valid-jwt-token-at-all"
        },
    )
    assert r.status_code == 401


async def test_me_after_user_deleted_returns_401(auth_client, tokens, user_repo):
    """A valid token for a user that no longer exists → 401."""
    ok = await auth_client.get(
        f"{API}/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert ok.status_code == 200

    user_repo._users.clear()
    user_repo._by_email.clear()
    user_repo._by_username.clear()

    r = await auth_client.get(
        f"{API}/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 401


async def test_login_wrong_password_returns_401(auth_client, registered):
    """POST /login with wrong password → 401.

    Covers the AuthenticationError branch in the login endpoint.
    """
    r = await auth_client.post(
        f"{API}/login",
        json={"email": _CREDS["email"], "password": "wrong-password"},
    )
    assert r.status_code == 401
