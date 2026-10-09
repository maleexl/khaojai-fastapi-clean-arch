"""SQLAlchemy implementation of :class:`TokenBlacklistRepository`."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.token_blacklist import TokenBlacklist
from app.domain.repositories.token_blacklist_repository import (
    TokenBlacklistRepository,
)
from app.infrastructure.database.models import TokenBlacklistModel


def _to_entity(model: TokenBlacklistModel) -> TokenBlacklist:
    """Map an ORM row to a domain entity."""
    return TokenBlacklist(
        id=None,
        jti=model.jti,
        expires_at=model.expires_at,
        created_at=model.created_at,
    )


class TokenBlacklistRepositoryImpl(TokenBlacklistRepository):
    """Async SQLAlchemy implementation of the blacklist contract."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session used for all operations."""
        self._session = session

    async def add(self, entry: TokenBlacklist) -> TokenBlacklist:
        model = TokenBlacklistModel(
            jti=entry.jti,
            expires_at=entry.expires_at,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def is_blacklisted(self, jti: str) -> bool:
        stmt = select(TokenBlacklistModel.jti).where(
            TokenBlacklistModel.jti == jti
        )
        return (await self._session.execute(stmt)).first() is not None
