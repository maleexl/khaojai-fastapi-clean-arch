"""Health check routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JSONResponse:
    """Report app + database liveness.

    Returns 200 when the DB responds to ``SELECT 1``; 503 otherwise.
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "disconnected"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "database": "connected"},
    )
