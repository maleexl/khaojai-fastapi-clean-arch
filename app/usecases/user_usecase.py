"""User use cases (application business logic).

Depends ONLY on the domain layer:
    - ``User`` / ``TokenBlacklist`` entities
    - ``UserRepository`` / ``TokenBlacklistRepository`` abstract interfaces
    - shared exceptions

No FastAPI, SQLAlchemy, Pydantic, or JWT import is allowed here.
Password hashing, token creation/decoding, and clock are injected as
callables so the usecase stays framework-free and easy to test.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from app.domain.entities.token_blacklist import TokenBlacklist
from app.domain.entities.user import User
from app.domain.repositories.token_blacklist_repository import (
    TokenBlacklistRepository,
)
from app.domain.repositories.user_repository import UserRepository
from app.shared.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

HashFn = Callable[[str], str]
VerifyFn = Callable[[str, str], bool]
AccessTokenFn = Callable[[UUID, str], str]
RefreshTokenFn = Callable[[UUID, str], str]
DecodeRefreshFn = Callable[[str], dict]


class UserUsecase:
    """Orchestrates user-related operations."""

    def __init__(
        self,
        user_repository: UserRepository,
        blacklist_repository: TokenBlacklistRepository,
        hash_password: HashFn,
        verify_password: VerifyFn,
        create_access_token: AccessTokenFn,
        create_refresh_token: RefreshTokenFn,
        decode_refresh_token: DecodeRefreshFn,
    ) -> None:
        """Inject dependencies via constructor (Dependency Inversion)."""
        self._repo = user_repository
        self._blacklist = blacklist_repository
        self._hash = hash_password
        self._verify = verify_password
        self._make_access = create_access_token
        self._make_refresh = create_refresh_token
        self._decode_refresh = decode_refresh_token

    # ---------- public use cases ----------

    async def register(
        self, email: str, username: str, password: str
    ) -> User:
        """Register a new user.

        Raises:
            ValidationError: If ``password`` is too short.
            ConflictError: If email or username already exists.
        """
        self._validate_password(password)
        email = email.strip().lower()
        username = username.strip()

        if await self._repo.exists_by_email(email):
            raise ConflictError("Email already registered")
        if await self._repo.exists_by_username(username):
            raise ConflictError("Username already taken")

        user = User(
            email=email,
            username=username,
            hashed_password=self._hash(password),
        )
        return await self._repo.create(user)

    async def login(self, email: str, password: str) -> tuple[str, str]:
        """Authenticate and return ``(access_token, refresh_token)``.

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        user = await self._repo.get_by_email(email.strip().lower())
        if user is None or not self._verify(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        assert user.id is not None
        return (
            self._make_access(user.id, user.email),
            self._make_refresh(user.id, user.email),
        )

    async def logout(self, refresh_token: str) -> None:
        """Blacklist the given refresh token so it can no longer be used.

        Raises:
            AuthenticationError: If the token is invalid, expired, or already
                blacklisted.
        """
        payload = self._decode_or_raise(refresh_token)
        if await self._blacklist.is_blacklisted(payload["jti"]):
            raise AuthenticationError("Token already revoked")

        entry = TokenBlacklist(
            jti=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
        await self._blacklist.add(entry)

    async def refresh_token(self, refresh_token: str) -> str:
        """Return a new access token for a valid refresh token.

        Raises:
            AuthenticationError: If the token is invalid, expired, or
                blacklisted.
        """
        payload = self._decode_or_raise(refresh_token)
        if await self._blacklist.is_blacklisted(payload["jti"]):
            raise AuthenticationError("Token has been revoked")

        user = await self._repo.get_by_id(UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        return self._make_access(user.id, user.email)

    async def get_by_id(self, user_id: UUID) -> User:
        """Return a user by id.

        Raises:
            NotFoundError: If no user with the given id exists.
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    # ---------- internals ----------

    def _decode_or_raise(self, token: str) -> dict:
        """Decode a refresh token, converting JWT errors to AuthenticationError."""
        try:
            return self._decode_refresh(token)
        except Exception as exc:  # e.g. expired/invalid signature
            raise AuthenticationError("Invalid or expired token") from exc

    @staticmethod
    def _validate_password(password: str) -> None:
        """Ensure password meets minimum policy."""
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
