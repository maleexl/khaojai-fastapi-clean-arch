"""Abstract TokenBlacklist repository interface (Dependency Inversion)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.token_blacklist import TokenBlacklist


class TokenBlacklistRepository(ABC):
    """Persistence contract for :class:`TokenBlacklist` entries."""

    @abstractmethod
    async def add(self, entry: TokenBlacklist) -> TokenBlacklist:
        """Persist a new blacklist entry."""

    @abstractmethod
    async def is_blacklisted(self, jti: str) -> bool:
        """Return ``True`` if the given ``jti`` has been revoked."""
