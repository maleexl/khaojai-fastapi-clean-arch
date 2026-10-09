"""User domain entity.

Pure-Python representation of a User. This module MUST NOT import any
framework, ORM, or validation library (no FastAPI, SQLAlchemy, Pydantic).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    """Domain entity representing an application user.

    Attributes:
        id: Unique identifier (``None`` before persistence).
        email: Unique email address.
        username: Unique display name.
        hashed_password: Password hash (never the plain password).
        is_active: Whether the account is allowed to log in.
        created_at: Creation timestamp (set by persistence layer).
        updated_at: Last-modification timestamp (set by persistence layer).
    """

    email: str
    username: str
    hashed_password: str
    id: UUID | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
