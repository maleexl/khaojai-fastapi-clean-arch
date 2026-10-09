"""Unit tests for ``UserUsecase``.

All tests run against in-memory fakes — no DB, no network, no docker.
This proves Dependency Inversion: the usecase depends on abstract
repository interfaces, so we can substitute fakes seamlessly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.domain.entities.user import User
from app.shared.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.usecases.user_usecase import UserUsecase
from tests.unit.fakes import (
    InMemoryTokenBlacklistRepository,
    InMemoryUserRepository,
)


class FakeTokenOps:
    """Deterministic stand-ins for hash/verify/JWT callables."""

    def __init__(self) -> None:
        self._tokens: dict[str, dict] = {}
        self._counter = 0

    @staticmethod
    def hash_password(password: str) -> str:
        return f"hashed::{password}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return hashed == f"hashed::{password}"

    def make_access(self, user_id: UUID, email: str) -> str:
        return f"access::{user_id}::{email}"

    def make_refresh(self, user_id: UUID, email: str) -> str:
        self._counter += 1
        jti = f"jti-{self._counter}"
        exp = int(
            (datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()
        )
        token = f"refresh::{jti}"
        self._tokens[token] = {
            "jti": jti,
            "sub": str(user_id),
            "exp": exp,
            "type": "refresh",
        }
        return token

    def decode_refresh(self, token: str) -> dict:
        if token not in self._tokens:
            raise ValueError(f"Unknown refresh token: {token!r}")
        return dict(self._tokens[token])


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def blacklist_repo() -> InMemoryTokenBlacklistRepository:
    return InMemoryTokenBlacklistRepository()


@pytest.fixture
def token_ops() -> FakeTokenOps:
    return FakeTokenOps()


@pytest.fixture
def usecase(
    user_repo: InMemoryUserRepository,
    blacklist_repo: InMemoryTokenBlacklistRepository,
    token_ops: FakeTokenOps,
) -> UserUsecase:
    """Usecase wired to fully in-memory dependencies."""
    return UserUsecase(
        user_repository=user_repo,
        blacklist_repository=blacklist_repo,
        hash_password=token_ops.hash_password,
        verify_password=token_ops.verify_password,
        create_access_token=token_ops.make_access,
        create_refresh_token=token_ops.make_refresh,
        decode_refresh_token=token_ops.decode_refresh,
    )


@pytest.fixture
def existing_user(user_repo: InMemoryUserRepository) -> User:
    """Pre-seeded user with hashed password 'hashed::password123'."""
    return user_repo.seed(
        User(
            email="alice@example.com",
            username="alice",
            hashed_password="hashed::password123",
        )
    )


async def test_register_success(usecase, user_repo):
    """register() creates user, lowercases email, trims username, hashes pw."""
    user = await usecase.register(
        email="New@Example.com",
        username="  newbie  ",
        password="supersecret",
    )

    assert user.id is not None
    assert user.email == "new@example.com"
    assert user.username == "newbie"
    assert user.hashed_password == "hashed::supersecret"
    assert user.hashed_password != "supersecret"
    assert user.is_active is True
    assert user.created_at is not None
    assert await user_repo.exists_by_email("new@example.com")


async def test_register_duplicate_email_raises(usecase, existing_user):
    """register() rejects an already-used email with ConflictError."""
    with pytest.raises(ConflictError, match="Email"):
        await usecase.register(
            email="alice@example.com",
            username="different-name",
            password="password123",
        )


async def test_register_duplicate_username_raises(usecase, existing_user):
    """register() rejects an already-used username with ConflictError."""
    with pytest.raises(ConflictError, match="Username"):
        await usecase.register(
            email="someone-else@example.com",
            username="alice",
            password="password123",
        )


async def test_register_short_password_raises(usecase):
    """register() rejects passwords shorter than 8 chars."""
    with pytest.raises(ValidationError, match="8 characters"):
        await usecase.register(
            email="x@example.com",
            username="x",
            password="short",
        )


async def test_login_success(usecase, existing_user):
    """login() returns a (access, refresh) pair for valid credentials."""
    access, refresh = await usecase.login(
        email="alice@example.com", password="password123"
    )
    assert access.startswith("access::")
    assert refresh.startswith("refresh::")


async def test_login_email_is_case_insensitive(usecase, existing_user):
    """login() normalises email case before lookup."""
    access, _ = await usecase.login(
        email="ALICE@example.com", password="password123"
    )
    assert access.startswith("access::")


async def test_login_wrong_password_raises(usecase, existing_user):
    """login() raises AuthenticationError on wrong password."""
    with pytest.raises(AuthenticationError):
        await usecase.login(
            email="alice@example.com", password="wrong-password"
        )


async def test_login_unknown_email_raises(usecase):
    """login() raises AuthenticationError when email is not registered."""
    with pytest.raises(AuthenticationError):
        await usecase.login(
            email="ghost@example.com", password="whatever123"
        )


async def test_login_inactive_user_raises(usecase, user_repo):
    """login() refuses disabled accounts."""
    user_repo.seed(
        User(
            email="bob@example.com",
            username="bob",
            hashed_password="hashed::password123",
            is_active=False,
        )
    )
    with pytest.raises(AuthenticationError, match="disabled"):
        await usecase.login(email="bob@example.com", password="password123")


async def test_logout_blacklists_jti(
    usecase, blacklist_repo, token_ops, existing_user
):
    """logout() persists a blacklist entry keyed by the token's jti."""
    _, refresh = await usecase.login(
        email=existing_user.email, password="password123"
    )
    payload = token_ops.decode_refresh(refresh)
    jti = payload["jti"]

    assert await blacklist_repo.is_blacklisted(jti) is False

    await usecase.logout(refresh)

    assert await blacklist_repo.is_blacklisted(jti) is True
    entries = blacklist_repo.entries
    assert len(entries) == 1
    assert entries[0].jti == jti
    assert entries[0].expires_at == datetime.fromtimestamp(
        payload["exp"], tz=timezone.utc
    )


async def test_logout_twice_raises(usecase, existing_user):
    """Calling logout() twice on the same token raises AuthenticationError."""
    _, refresh = await usecase.login(
        email=existing_user.email, password="password123"
    )
    await usecase.logout(refresh)

    with pytest.raises(AuthenticationError, match="already revoked"):
        await usecase.logout(refresh)


async def test_logout_invalid_token_raises(usecase):
    """logout() raises AuthenticationError for an undecodable token."""
    with pytest.raises(AuthenticationError):
        await usecase.logout("not-a-real-token")


async def test_refresh_token_returns_new_access(usecase, existing_user):
    """refresh_token() returns a new access token for a valid refresh token."""
    _, refresh = await usecase.login(
        email=existing_user.email, password="password123"
    )
    new_access = await usecase.refresh_token(refresh)
    assert new_access.startswith("access::")
    assert str(existing_user.id) in new_access


async def test_refresh_token_after_logout_raises(usecase, existing_user):
    """A blacklisted refresh token cannot be used to refresh."""
    _, refresh = await usecase.login(
        email=existing_user.email, password="password123"
    )
    await usecase.logout(refresh)

    with pytest.raises(AuthenticationError, match="revoked"):
        await usecase.refresh_token(refresh)


async def test_refresh_token_unknown_user_raises(usecase, token_ops):
    """If the user referenced in the token no longer exists, refresh fails."""
    orphan_token = token_ops.make_refresh(uuid4(), "ghost@example.com")
    with pytest.raises(AuthenticationError, match="not found"):
        await usecase.refresh_token(orphan_token)


async def test_refresh_token_invalid_raises(usecase):
    """refresh_token() raises AuthenticationError for an undecodable token."""
    with pytest.raises(AuthenticationError):
        await usecase.refresh_token("garbage")


async def test_get_by_id_success(usecase, existing_user):
    """get_by_id() returns the stored user."""
    user = await usecase.get_by_id(existing_user.id)
    assert user.id == existing_user.id
    assert user.email == existing_user.email


async def test_get_by_id_not_found_raises(usecase):
    """get_by_id() raises NotFoundError for an unknown id."""
    with pytest.raises(NotFoundError):
        await usecase.get_by_id(uuid4())
