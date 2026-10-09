"""FastAPI application entrypoint."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.interface.api.v1.routers.health_router import router as health_router
from app.interface.api.v1.routers.user_router import router as user_router
from app.shared.exceptions import (
    AppException,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application startup / shutdown hooks."""
    yield


_STATUS_MAP: dict[type[AppException], int] = {
    ValidationError: 400,
    AuthenticationError: 401,
    NotFoundError: 404,
    ConflictError: 409,
}


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
        version="1.1.0",
    )

    @app.exception_handler(AppException)
    async def _app_exception_handler(
        _: Request, exc: AppException
    ) -> JSONResponse:
        status_code = _STATUS_MAP.get(type(exc), 500)
        return JSONResponse(
            status_code=status_code, content={"detail": exc.message}
        )

    app.include_router(health_router)
    app.include_router(user_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
