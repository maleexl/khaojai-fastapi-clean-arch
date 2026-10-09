"""Security helpers: password hashing + JWT access/refresh tokens.

Access tokens are short-lived (15 min) and used for API calls.
Refresh tokens are long-lived (7 days) and only used to obtain new
access tokens via ``/users/refresh-token``.

Both token kinds carry a ``jti`` claim (JWT ID) so they can be
individually blacklisted on logout.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import bcrypt
from jose import JWTError, jwt

from app.config.settings import settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


# ---------- password ----------

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if ``plain`` matches the bcrypt ``hashed`` value."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------- JWT internals ----------

def _encode(payload: dict, expires_delta: timedelta) -> str:
    """Sign a JWT payload with ``iat`` / ``exp`` / ``jti`` set."""
    now = datetime.now(timezone.utc)
    to_encode = {
        **payload,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


# ---------- public token factories ----------

def create_access_token(user_id: UUID, email: str) -> str:
    """Create a short-lived JWT access token (``ACCESS_TOKEN_EXPIRE_MINUTES``)."""
    return _encode(
        {"sub": str(user_id), "email": email, "type": TOKEN_TYPE_ACCESS},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: UUID, email: str) -> str:
    """Create a long-lived JWT refresh token (``REFRESH_TOKEN_EXPIRE_DAYS``)."""
    return _encode(
        {"sub": str(user_id), "email": email, "type": TOKEN_TYPE_REFRESH},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


# ---------- decoding ----------

def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Decode a JWT and optionally enforce its ``type`` claim.

    Args:
        token: Encoded JWT string.
        expected_type: ``"access"`` or ``"refresh"`` (or ``None`` to skip).

    Raises:
        JWTError: If the token is invalid, expired, or has the wrong type.
    """
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    if expected_type is not None and payload.get("type") != expected_type:
        raise JWTError(
            f"Invalid token type: expected '{expected_type}', "
            f"got '{payload.get('type')}'"
        )
    return payload


def decode_access_token(token: str) -> dict:
    """Decode a JWT access token (backward-compatible helper)."""
    return decode_token(token, TOKEN_TYPE_ACCESS)


def decode_refresh_token(token: str) -> dict:
    """Decode a JWT refresh token."""
    return decode_token(token, TOKEN_TYPE_REFRESH)
