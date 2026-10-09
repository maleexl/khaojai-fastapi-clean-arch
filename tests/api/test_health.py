"""API tests for ``GET /health``.

Verifies that the endpoint reports 200 when the DB responds, and 503
when it does not — using a fake AsyncSession injected via
``app.dependency_overrides``. No real DB required.
"""
from __future__ import annotations

from app.infrastructure.database.session import get_session


async def test_health_returns_200_when_db_ok(app, client, fake_session_ok):
    """GET /health → 200 with {status: ok, database: connected}."""
    app.dependency_overrides[get_session] = lambda: fake_session_ok

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


async def test_health_returns_503_when_db_down(app, client, fake_session_fail):
    """GET /health → 503 with {status: degraded, database: disconnected}."""
    app.dependency_overrides[get_session] = lambda: fake_session_fail

    response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "disconnected",
    }
