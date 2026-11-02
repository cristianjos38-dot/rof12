from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import AuthContext, get_auth_context
from app.security.hold_manager import HoldError, HoldManager

router = APIRouter(prefix="/v1/holds", tags=["holds"])
hold_manager = HoldManager()


class HoldResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool


@router.get("")
def list_holds(context: AuthContext = Depends(get_auth_context)):
    return [hold.__dict__ for hold in hold_manager.holds.values() if hold.tenant_id == context.tenant_id]


@router.get("/{hold_id}")
def get_hold(hold_id: str, context: AuthContext = Depends(get_auth_context)):
    hold = hold_manager.holds.get(hold_id)
    if hold is None or hold.tenant_id != context.tenant_id:
        raise HTTPException(404, detail="hold not found")
    return {"hold_id": hold.hold_id, "status": hold.status, "expires_at": hold.expires_at, "evidence": {}}


@router.post("/{hold_id}/resolve")
def resolve_hold(hold_id: str, payload: HoldResolution, context: AuthContext = Depends(get_auth_context)):
    try:
        hold = hold_manager.resolve(hold_id, context, datetime.now(UTC), payload.approve, lambda: type("Revalidation", (), {"decision": "ALLOW"})())
    except HoldError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    return {"hold_id": hold.hold_id, "status": hold.status}

