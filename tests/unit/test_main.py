"""Unit tests for app.main — application wiring.

Covers the lifespan context manager in isolation so we don't need
a real DB or HTTP server to exercise it.
"""
from __future__ import annotations

from fastapi import FastAPI

from app.main import create_app, lifespan


async def test_lifespan_enters_and_exits_cleanly() -> None:
    """The app lifespan context manager yields without raising."""
    app = FastAPI()
    async with lifespan(app):
        pass


def test_create_app_returns_fastapi_instance() -> None:
    """create_app() returns a FastAPI app with the expected routes mounted.

    Uses app.openapi() (the public contract) rather than iterating
    app.routes — newer Starlette wraps included routers in objects that
    lack a .path attribute.
    """
    app = create_app()
    assert isinstance(app, FastAPI)

    paths = set(app.openapi()["paths"].keys())
    assert "/health" in paths
    assert "/api/v1/users/register" in paths
    assert "/api/v1/users/login" in paths
    assert "/api/v1/users/me" in paths
    assert "/api/v1/users/refresh-token" in paths
    assert "/api/v1/users/logout" in paths
