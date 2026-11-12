from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.responses import Response

from app.api.dependencies import AuthContext, get_auth_context
from app.api.routes.holds import hold_manager
from app.api.state import api_state
from app.db.connection import create_app_engine
from app.security.kill_switch import KillSwitch
from sqlalchemy.exc import SQLAlchemyError

_UI_ROOT = Path(__file__).resolve().parent
_templates = Jinja2Templates(
    env=Environment(
        loader=FileSystemLoader(_UI_ROOT / "templates"),
        autoescape=select_autoescape(("html", "xml"), default=True),
    ),
)

router = APIRouter(prefix="/ui", tags=["control-panel"])
def _tenant_holds(context: AuthContext) -> list[dict]:
    return [
        {
            "hold_id": hold.hold_id,
            "status": hold.status.value,
            "created_by": hold.created_by,
            "expires_at": hold.expires_at.isoformat(),
        }
        for hold in hold_manager.holds.values()
        if hold.tenant_id == context.tenant_id
    ]


def _tenant_artifacts(context: AuthContext) -> list[dict]:
    with api_state.lock:
        return [
            dict(artifact)
            for (tenant_id, _artifact_id), artifact in api_state.artifacts.items()
            if tenant_id == context.tenant_id
        ]


def _kill_switch_active() -> bool:
    try:
        with create_app_engine().begin() as connection:
            return KillSwitch().read(connection).active
    except SQLAlchemyError:
        return False


def _render(template: str, request: Request, context: AuthContext, **extra) -> Response:
    data = {
        "request": request,
        "auth": context,
        "holds": _tenant_holds(context),
        "artifacts": _tenant_artifacts(context),
        "kill_switch_active": _kill_switch_active(),
        **extra,
    }
    response = _templates.TemplateResponse(request=request, name=template, context=data)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/")
def dashboard(request: Request, context: AuthContext = Depends(get_auth_context)) -> Response:  # noqa: B008
    return _render("dashboard.html", request, context)


@router.get("/partials/holds")
def holds_partial(request: Request, context: AuthContext = Depends(get_auth_context)) -> Response:  # noqa: B008
    return _render("partials/holds.html", request, context)


@router.get("/partials/artifacts")
def artifacts_partial(request: Request, context: AuthContext = Depends(get_auth_context)) -> Response:  # noqa: B008
    return _render("partials/artifacts.html", request, context)


@router.get("/partials/security")
def security_partial(request: Request, context: AuthContext = Depends(get_auth_context)) -> Response:  # noqa: B008
    return _render("partials/security.html", request, context)
