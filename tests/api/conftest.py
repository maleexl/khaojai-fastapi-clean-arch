"""Shared fixtures for API tests.

Strategy:
    - Use httpx.AsyncClient + ASGITransport against the real FastAPI app
      built by ``create_app()``.
    - Replace the DB dependency (``get_session``) with a fake AsyncSession
      via ``app.dependency_overrides``.
    - No real DB, no docker, no network.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


class FakeSession:
    """Minimal stand-in for ``AsyncSession``."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.executed: list[Any] = []

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> None:
        self.executed.append(statement)
        if self.fail:
            raise RuntimeError("simulated DB failure")


@pytest.fixture
def app():
    """Fresh FastAPI app per test (avoids shared dependency_overrides)."""
    return create_app()


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    """httpx.AsyncClient talking to the app in-process (no network)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture
def fake_session_ok() -> FakeSession:
    """Fake session where ``execute`` succeeds (DB healthy)."""
    return FakeSession(fail=False)


@pytest.fixture
def fake_session_fail() -> FakeSession:
    """Fake session where ``execute`` raises (DB down)."""
    return FakeSession(fail=True)


# ---------------------------------------------------------------------------
# Auth-flow fixtures (Step 6)
# ---------------------------------------------------------------------------

from app.infrastructure.database.session import get_session
from app.interface.api.v1.routers import user_router as _user_router_module
from app.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.usecases.user_usecase import UserUsecase
from tests.unit.fakes import (
    InMemoryTokenBlacklistRepository,
    InMemoryUserRepository,
)


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    """Fresh in-memory user repo per test."""
    return InMemoryUserRepository()


@pytest.fixture
def blacklist_repo() -> InMemoryTokenBlacklistRepository:
    """Fresh in-memory blacklist repo per test."""
    return InMemoryTokenBlacklistRepository()


@pytest.fixture
async def auth_client(
    app, user_repo, blacklist_repo, monkeypatch
) -> AsyncIterator[AsyncClient]:
    """AsyncClient with the router's _get_usecase swapped for a fake."""

    async def _fake_get_session():
        yield None

    app.dependency_overrides[get_session] = _fake_get_session

    def _fake_get_usecase(_session):
        return UserUsecase(
            user_repository=user_repo,
            blacklist_repository=blacklist_repo,
            hash_password=hash_password,
            verify_password=verify_password,
            create_access_token=create_access_token,
            create_refresh_token=create_refresh_token,
            decode_refresh_token=decode_refresh_token,
        )

    monkeypatch.setattr(
        _user_router_module, "_get_usecase", _fake_get_usecase
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        yield ac
