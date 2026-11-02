from fastapi import APIRouter, Depends, Request

from app.api.dependencies import AuthContext
from app.api.security_dependencies import get_security_context
from app.api.state import api_state
from app.security.kill_switch import KillSwitch

router = APIRouter(prefix="/v1/security", tags=["security"])
kill_switch = KillSwitch()


class SecurityAction:
    pass


@router.get("/status")
def security_status(context: AuthContext = Depends(get_security_context)):
    return {"kill_switch_active": api_state.kill_switch_active, "reason": api_state.kill_reason}


@router.post("/kill-switch")
def activate_kill_switch(request: Request, context: AuthContext = Depends(get_security_context)):
    with api_state.lock:
        api_state.kill_switch_active = True
        api_state.kill_reason = "activated by %s from %s" % (context.user_id, request.client.host if request.client else "unknown")
        for key in list(api_state.audit):
            pass
    return {"kill_switch_active": True, "request_id": request.state.request_id}


@router.post("/recovery")
def recover(request: Request, context: AuthContext = Depends(get_security_context)):
    with api_state.lock:
        api_state.kill_switch_active = False
        api_state.kill_reason = ""
    return {"kill_switch_active": False, "request_id": request.state.request_id}

