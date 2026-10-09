"""SQLAlchemy implementation of :class:`UserRepository` (Interface layer).

Maps between ORM models (infrastructure) and domain entities (domain).
This is the ONLY place that knows both worlds.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.models import UserModel


def _to_entity(model: UserModel) -> User:
    """Map an ORM :class:`UserModel` to a domain :class:`User`."""
    return User(
        id=model.id,
        email=model.email,
        username=model.username,
        hashed_password=model.hashed_password,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class UserRepositoryImpl(UserRepository):
    """Async SQLAlchemy implementation of the user repository contract."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session used for all operations."""
        self._session = session

    async def create(self, user: User) -> User:
        model = UserModel(
            email=user.email,
            username=user.username,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.get(UserModel, user_id)
        return _to_entity(result) if result else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(UserModel).where(UserModel.username == username)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_entity(model) if model else None

    async def exists_by_email(self, email: str) -> bool:
        stmt = select(UserModel.id).where(UserModel.email == email)
        return (await self._session.execute(stmt)).first() is not None

    async def exists_by_username(self, username: str) -> bool:
        stmt = select(UserModel.id).where(UserModel.username == username)
        return (await self._session.execute(stmt)).first() is not None
