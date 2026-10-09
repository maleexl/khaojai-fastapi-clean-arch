"""Domain / Usecase exceptions.

Framework-agnostic. The Interface layer (routers) is responsible for
translating these into HTTP responses.
"""
from __future__ import annotations


class AppException(Exception):
    """Base class for all application-level exceptions."""

    def __init__(self, message: str = "Application error") -> None:
        self.message = message
        super().__init__(message)


class ValidationError(AppException):
    """Input violates a business rule (e.g. weak password)."""


class ConflictError(AppException):
    """Resource already exists (e.g. duplicate email/username)."""


class NotFoundError(AppException):
    """Requested resource does not exist."""


class AuthenticationError(AppException):
    """Credentials are invalid or token is unusable."""
