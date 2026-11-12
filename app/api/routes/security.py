from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import AuthContext
from app.api.security_dependencies import get_security_context
from app.db.connection import create_app_engine, create_executor_engine
from app.security.kill_switch import KillSwitch, KillSwitchError

router = APIRouter(prefix="/v1/security", tags=["security"])
kill_switch = KillSwitch()


@router.get("/status")
def security_status(context: AuthContext = Depends(get_security_context)):
    try:
        with create_app_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            state = kill_switch.read(connection)
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail="security state unavailable") from exc
    return {"kill_switch_active": state.active, "reason": state.reason}


@router.post("/kill-switch")
def activate_kill_switch(request: Request, context: AuthContext = Depends(get_security_context)):
    reason = f"activated by {context.user_id} from {request.client.host if request.client else 'unknown'}"
    try:
        with create_executor_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            state = kill_switch.activate(connection, context, reason)
    except (SQLAlchemyError, KillSwitchError) as exc:
        raise HTTPException(503, detail="kill switch could not be activated") from exc
    return {"kill_switch_active": state.active, "request_id": request.state.request_id}


@router.post("/recovery")
def recover(request: Request, context: AuthContext = Depends(get_security_context)):
    try:
        with create_executor_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            state = kill_switch.deactivate(connection, context)
    except (SQLAlchemyError, KillSwitchError) as exc:
        raise HTTPException(503, detail="kill switch could not be recovered") from exc
    return {"kill_switch_active": state.active, "request_id": request.state.request_id}
