from .artifacts import router as artifacts_router
from .assertions import router as assertions_router
from .audit import router as audit_router
from .audit import internal_router as audit_internal_router
from .datasets import router as datasets_router
from .evidence import router as evidence_router
from .exports import router as exports_router
from .gateway import router as gateway_router
from .manuscripts import router as manuscripts_router
from .projects import router as projects_router
from .reviews import router as reviews_router
from .templates import router as templates_router
from .workflows import router as workflows_router

ROUTERS = (
    templates_router,
    gateway_router,
    projects_router,
    datasets_router,
    workflows_router,
    artifacts_router,
    assertions_router,
    evidence_router,
    manuscripts_router,
    reviews_router,
    exports_router,
    audit_router,
    audit_internal_router,
)

__all__ = ["ROUTERS"]
