from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.api.exceptions import (
    ApiDomainError,
    domain_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.api.middleware import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.routes.artifacts import router as artifacts_router
from app.api.routes.audit import router as audit_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.holds import router as holds_router
from app.api.routes.security import router as security_router
from app.api.routes.tasks import router as tasks_router
from app.api.routes.tasks import evaluate_router, v1_router as v1_tasks_router
from app.api.routes.refunds import router as refunds_router
from app.api.n8n import router as n8n_router
from app.ui.routes import router as ui_router

app = FastAPI(title="ROF12", version="0.1.0")
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ApiDomainError, domain_exception_handler)  # type: ignore[arg-type]
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(tasks_router)
app.include_router(v1_tasks_router)
app.include_router(evaluate_router)
app.include_router(refunds_router)
app.include_router(n8n_router)
app.include_router(documents_router)
app.include_router(artifacts_router)
app.include_router(audit_router)
app.include_router(holds_router)
app.include_router(security_router)
app.include_router(ui_router)
app.mount("/ui/static", StaticFiles(directory=Path(__file__).resolve().parent / "ui" / "static"), name="ui-static")

