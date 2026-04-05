from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .auth import bind_auth_context, reset_auth_context, resolve_auth_context
from .routers import ROUTERS
from .services.base import ServiceNotImplementedError


def create_app() -> FastAPI:
    app = FastAPI(
        title="DR-OS Control Plane",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

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
