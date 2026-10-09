"""TokenBlacklist domain entity.

Pure-Python representation of a revoked JWT. This module MUST NOT import
any framework, ORM, or validation library.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class TokenBlacklist:
    """A revoked JWT entry.

    Attributes:
        jti: JWT ID (unique per token).
        expires_at: Original token expiry — used to prune old rows.
        id: Row identifier (``None`` before persistence).
        created_at: When the token was blacklisted.
    """

    jti: str
    expires_at: datetime
    id: UUID | None = None
    created_at: datetime | None = None
