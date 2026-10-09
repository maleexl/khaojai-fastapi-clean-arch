"""In-memory fakes for the repository interfaces.

These fakes implement the SAME abstract interfaces (``UserRepository``,
``TokenBlacklistRepository``) as the production repositories. That is the
whole point of Dependency Inversion: the usecase under test cannot tell
the difference between a fake and a real DB-backed repository.

No DB, no network, no docker required.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.token_blacklist import TokenBlacklist
from app.domain.entities.user import User
from app.domain.repositories.token_blacklist_repository import (
    TokenBlacklistRepository,
)
from app.domain.repositories.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    """Dict-backed implementation of :class:`UserRepository`."""

    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}
        self._by_email: dict[str, UUID] = {}
        self._by_username: dict[str, UUID] = {}

    @property
    def users(self) -> list[User]:
        """Snapshot of all stored users (read-only view for assertions)."""
        return list(self._users.values())

    def seed(self, user: User) -> User:
        """Insert a user directly, bypassing usecase validation."""
        if user.id is None:
            user = replace(user, id=uuid4())
        if user.created_at is None:
            user = replace(user, created_at=datetime.now(timezone.utc))
        if user.updated_at is None:
            user = replace(user, updated_at=user.created_at)

        self._users[user.id] = user
        self._by_email[user.email.lower()] = user.id
        self._by_username[user.username] = user.id
        return replace(user)

    async def create(self, user: User) -> User:
        new_id = user.id or uuid4()
        now = datetime.now(timezone.utc)
        persisted = replace(
            user,
            id=new_id,
            created_at=user.created_at or now,
            updated_at=user.updated_at or now,
        )
        self._users[new_id] = persisted
        self._by_email[persisted.email.lower()] = new_id
        self._by_username[persisted.username] = new_id
        return replace(persisted)

    async def get_by_id(self, user_id: UUID) -> User | None:
        user = self._users.get(user_id)
        return replace(user) if user is not None else None

    async def get_by_email(self, email: str) -> User | None:
        uid = self._by_email.get(email.lower())
        if uid is None:
            return None
        return await self.get_by_id(uid)

    async def get_by_username(self, username: str) -> User | None:
        uid = self._by_username.get(username)
        if uid is None:
            return None
        return await self.get_by_id(uid)

    async def exists_by_email(self, email: str) -> bool:
        return email.lower() in self._by_email

    async def exists_by_username(self, username: str) -> bool:
        return username in self._by_username


class InMemoryTokenBlacklistRepository(TokenBlacklistRepository):
    """Dict-backed implementation of :class:`TokenBlacklistRepository`."""

    def __init__(self) -> None:
        self._entries: dict[str, TokenBlacklist] = {}

    @property
    def entries(self) -> list[TokenBlacklist]:
        """Snapshot of all blacklist entries (for assertions)."""
        return list(self._entries.values())

    def seed(self, entry: TokenBlacklist) -> TokenBlacklist:
        """Insert a blacklist entry directly (Arrange phase shortcut)."""
        if entry.id is None:
            entry = replace(entry, id=uuid4())
        if entry.created_at is None:
            entry = replace(entry, created_at=datetime.now(timezone.utc))
        self._entries[entry.jti] = entry
        return replace(entry)

    async def add(self, entry: TokenBlacklist) -> TokenBlacklist:
        now = datetime.now(timezone.utc)
        stored = replace(
            entry,
            id=entry.id or uuid4(),
            created_at=entry.created_at or now,
        )
        self._entries[stored.jti] = stored
        return replace(stored)

    async def is_blacklisted(self, jti: str) -> bool:
        return jti in self._entries
