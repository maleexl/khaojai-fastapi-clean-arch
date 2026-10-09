"""Abstract User repository interface (Dependency Inversion boundary).

The Usecase layer depends on THIS abstraction, never on the concrete
implementation (which lives in ``app.interface.repositories``).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.user import User


class UserRepository(ABC):
    """Persistence contract for :class:`User` entities."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persist a new user and return it with generated fields set."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user with the given id, or ``None`` if not found."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Return the user with the given email, or ``None`` if not found."""

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        """Return the user with the given username, or ``None`` if not found."""

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        """Return ``True`` if a user with the given email exists."""

    @abstractmethod
    async def exists_by_username(self, username: str) -> bool:
        """Return ``True`` if a user with the given username exists."""
