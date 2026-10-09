"""User HTTP routes (Interface layer).

- Manual dependency injection (no DI framework).
- Translates usecase/domain exceptions into HTTPException.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.domain.entities.user import User
from app.infrastructure.database.session import get_session
from app.interface.api.v1.schemas.token_schema import (
    AccessTokenResponse,
    MessageResponse,
    RefreshTokenRequest,
)
from app.interface.api.v1.schemas.user_schema import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.interface.repositories.token_blacklist_repository_impl import (
    TokenBlacklistRepositoryImpl,
)
from app.interface.repositories.user_repository_impl import UserRepositoryImpl
from app.shared.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.usecases.user_usecase import UserUsecase

router = APIRouter(prefix="/users", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/users/login"
)


# ---------- manual DI ----------

def _get_usecase(session: AsyncSession) -> UserUsecase:
    """Build a fully-wired :class:`UserUsecase`."""
    return UserUsecase(
        user_repository=UserRepositoryImpl(session),
        blacklist_repository=TokenBlacklistRepositoryImpl(session),
        hash_password=hash_password,
        verify_password=verify_password,
        create_access_token=create_access_token,
        create_refresh_token=create_refresh_token,
        decode_refresh_token=decode_refresh_token,
    )


# ---------- auth dependency ----------

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Decode the access token and return the authenticated user."""
    creds_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise creds_error

    try:
        return await _get_usecase(session).get_by_id(user_id)
    except NotFoundError:
        raise creds_error


# ---------- exception translation ----------

def _handle_app_exception(exc: Exception) -> HTTPException:
    """Map domain/usecase exceptions to HTTP status codes."""
    if isinstance(exc, ValidationError):
        return HTTPException(status.HTTP_400_BAD_REQUEST, exc.message)
    if isinstance(exc, ConflictError):
        return HTTPException(status.HTTP_409_CONFLICT, exc.message)
    if isinstance(exc, AuthenticationError):
        return HTTPException(status.HTTP_401_UNAUTHORIZED, exc.message)
    if isinstance(exc, NotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, exc.message)
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal error")


# ---------- endpoints ----------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserRegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """Register a new user."""
    try:
        user = await _get_usecase(session).register(
            email=payload.email,
            username=payload.username,
            password=payload.password,
        )
    except (ValidationError, ConflictError) as exc:
        raise _handle_app_exception(exc)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Authenticate and return both access and refresh tokens."""
    try:
        access, refresh = await _get_usecase(session).login(
            payload.email, payload.password
        )
    except AuthenticationError as exc:
        raise _handle_app_exception(exc)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh-token", response_model=AccessTokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AccessTokenResponse:
    """Exchange a valid refresh token for a fresh access token."""
    try:
        new_access = await _get_usecase(session).refresh_token(
            payload.refresh_token
        )
    except AuthenticationError as exc:
        raise _handle_app_exception(exc)
    return AccessTokenResponse(
        access_token=new_access,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageResponse:
    """Blacklist the supplied refresh token."""
    try:
        await _get_usecase(session).logout(token)
    except AuthenticationError as exc:
        raise _handle_app_exception(exc)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)
