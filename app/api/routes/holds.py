from __future__ import annotations

import os
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import AuthContext, get_auth_context
from app.db.connection import create_executor_engine
from app.domain.contracts import ToolRequest
from app.security.capability_manager import CapabilityRecord, CapabilityStatus, hash_capability
from app.security.hold_manager import HoldError, HoldManager
from app.services.hold_service import HoldService
from app.services.refund_workflow import RefundWorkflow
from app.security.policy_engine import GateDecision

router = APIRouter(prefix="/v1/holds", tags=["holds"])
hold_manager = HoldManager()


class HoldResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool
    justification: str = ""


def _db_enabled() -> bool:
    return bool(os.getenv("DATABASE_URL"))


@router.get("")
def list_holds(context: AuthContext = Depends(get_auth_context)):
    if not _db_enabled():
        return [hold.__dict__ for hold in hold_manager.holds.values() if hold.tenant_id == context.tenant_id]
    try:
        with create_executor_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            rows = connection.execute(text("SELECT hold_id, tenant_id, operation_id, created_by, status, expires_at, resolved_by FROM rof12.holds ORDER BY created_at DESC")).mappings().all()
            return [dict(row) for row in rows]
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail="holds unavailable") from exc


@router.get("/{hold_id}")
def get_hold(hold_id: str, context: AuthContext = Depends(get_auth_context)):
    if not _db_enabled():
        hold = hold_manager.holds.get(hold_id)
        if hold is None or hold.tenant_id != context.tenant_id:
            raise HTTPException(404, detail="hold not found")
        return {"hold_id": hold.hold_id, "status": hold.status, "expires_at": hold.expires_at, "evidence": {}}
    try:
        with create_executor_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            row = connection.execute(text("SELECT hold_id, tenant_id, operation_id, created_by, status, expires_at, resolved_by, proposal FROM rof12.holds WHERE hold_id = :hold_id").bindparams(hold_id=hold_id)).mappings().first()
            if row is None:
                raise HTTPException(404, detail="hold not found")
            return dict(row)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail="hold unavailable") from exc


@router.post("/{hold_id}/resolve")
def resolve_hold(
    hold_id: str,
    payload: HoldResolution,
    context: AuthContext = Depends(get_auth_context),
    capability_token: str | None = Header(default=None, alias="X-Capability-Token"),
):
    if not _db_enabled():
        try:
            hold = hold_manager.resolve(
                hold_id, context, datetime.now(UTC), payload.approve,
                lambda: SimpleNamespace(decision=GateDecision.DENY), payload.justification,
            )
        except HoldError as exc:
            raise HTTPException(409, detail=str(exc)) from exc
        return {"hold_id": hold.hold_id, "status": hold.status, "approver_id": hold.approver_id, "justification": hold.justification}
    if payload.approve and not capability_token:
        raise HTTPException(401, detail="capability token required for revalidation")
    try:
        with create_executor_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            row = connection.execute(text("SELECT * FROM rof12.holds WHERE hold_id = :hold_id").bindparams(hold_id=hold_id)).mappings().first()
            if row is None:
                raise HTTPException(404, detail="hold not found")
            proposal = row["proposal"]
            request = ToolRequest(**proposal)
            capability_row = connection.execute(text("""
                SELECT capability_id, tenant_id, subject_user_id, token_hash, status, expires_at, max_amount
                  FROM rof12.capabilities WHERE token_hash = :token_hash AND tenant_id = :tenant_id
            """), {"token_hash": hash_capability(capability_token or ""), "tenant_id": context.tenant_id}).mappings().first()
            capability = None if capability_row is None else CapabilityRecord(
                capability_row["capability_id"], capability_row["tenant_id"], capability_row["subject_user_id"], capability_row["token_hash"], CapabilityStatus(capability_row["status"]), capability_row["expires_at"], capability_row["max_amount"]
            )
            def revalidate_and_execute():
                return RefundWorkflow().execute_transaction(
                    connection, context, request, capability,
                    SimpleNamespace(is_tainted=False),
                    SimpleNamespace(risk_level="LOW"), datetime.now(UTC), capability_token,
                )

            result = HoldService(connection).resolve(
                hold_id, context, payload.approve,
                revalidate_and_execute if payload.approve else lambda: SimpleNamespace(decision=GateDecision.ALLOW),
                payload.justification,
            )
            status = result
            return {"hold_id": hold_id, "status": status, "approver_id": context.user_id, "justification": payload.justification}
    except HTTPException:
        raise
    except (SQLAlchemyError, HoldError) as exc:
        raise HTTPException(409, detail=str(exc)) from exc
