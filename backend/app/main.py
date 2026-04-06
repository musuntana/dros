from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .auth import bind_auth_context, reset_auth_context, resolve_auth_context
from .routers import ROUTERS
from .services.base import ServiceNotImplementedError
from .settings import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="DR-OS Control Plane",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    settings = get_settings()

    if settings.ledger_backend == "postgres_rowlevel":

        @app.on_event("startup")
        def _init_pg_pool() -> None:
            from .db.pool import init_pool

            assert settings.postgres_dsn is not None
            init_pool(
                settings.postgres_dsn,
                min_size=settings.postgres_pool_min,
                max_size=settings.postgres_pool_max,
                schema=settings.postgres_schema,
            )
            logger.info("PostgreSQL row-level pool initialised (schema=%s)", settings.postgres_schema)

        @app.on_event("shutdown")
        def _close_pg_pool() -> None:
            from .db.pool import close_pool

            close_pool()
            logger.info("PostgreSQL row-level pool closed")

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(ServiceNotImplementedError)
    async def handle_not_implemented(_, exc: ServiceNotImplementedError) -> JSONResponse:
        return JSONResponse(status_code=501, content={"detail": str(exc)})

    @app.middleware("http")
    async def bind_request_auth_context(request, call_next):
        try:
            context = resolve_auth_context(request)
        except HTTPException as exc:
            content = {"detail": exc.detail}
            headers = exc.headers or {}
            return JSONResponse(status_code=exc.status_code, content=content, headers=headers)
        request.state.auth_context = context
        token = bind_auth_context(context)
        try:
            return await call_next(request)
        finally:
            reset_auth_context(token)

    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()
