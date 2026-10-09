"""Pydantic v2 schemas for token refresh / logout."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RefreshTokenRequest(BaseModel):
    """Payload for ``POST /users/refresh-token``."""

    refresh_token: str = Field(min_length=10)


class AccessTokenResponse(BaseModel):
    """Response for ``POST /users/refresh-token``."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class MessageResponse(BaseModel):
    """Simple ``{"message": "..."}`` response."""

    message: str
