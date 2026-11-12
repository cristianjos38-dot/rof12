from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, condecimal
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.dependencies import AuthContext, get_auth_context
from app.db.connection import create_executor_engine
from app.domain.contracts import ToolRequest
from app.security.capability_manager import CapabilityRecord, CapabilityStatus, hash_capability
from app.services.refund_workflow import RefundWorkflow

router = APIRouter(prefix="/v1/refunds", tags=["refunds"])


class RefundExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: str
    amount: condecimal(max_digits=12, decimal_places=2, gt=0)
    reason: str
    operation_id: str


def _load_capability(connection, token: str, context: AuthContext):
    row = connection.execute(text("""
        SELECT capability_id, tenant_id, subject_user_id, token_hash, status, expires_at, max_amount
          FROM rof12.capabilities
         WHERE token_hash = :token_hash AND tenant_id = :tenant_id
    """), {"token_hash": hash_capability(token), "tenant_id": context.tenant_id}).mappings().first()
    if row is None:
        return None
    return CapabilityRecord(
        row["capability_id"], row["tenant_id"], row["subject_user_id"], row["token_hash"],
        CapabilityStatus(row["status"]), row["expires_at"], row["max_amount"],
    )


@router.post("")
def execute_refund(
    payload: RefundExecutionRequest,
    context: AuthContext = Depends(get_auth_context),
    capability_token: str | None = Header(default=None, alias="X-Capability-Token"),
):
    """Execute a structured refund after database-backed revalidation.

    Structured JSON carries no document provenance, so this path defaults to
    ``is_tainted=False`` and ``risk_level=LOW``. Its security boundary is the
    server-resolved identity, capability, order state, limits, idempotency and
    kill switch. An order ID or amount copied from a poisoned document is not
    detected by taint tracking on this endpoint; document ingestion must be
    used when provenance analysis is required.
    """
    if not capability_token:
        raise HTTPException(401, detail="capability token required")
    request = ToolRequest(
        order_id=payload.order_id,
        amount=payload.amount,
        reason=payload.reason,
        operation_id=payload.operation_id,
    )
    proposal_hash = hashlib.sha256(json.dumps({
        "tenant_id": context.tenant_id,
        "operation_id": request.operation_id,
        "order_id": request.order_id,
        "amount": str(request.amount),
    }, sort_keys=True).encode()).hexdigest()
    try:
        with create_executor_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            capability = _load_capability(connection, capability_token, context)
            result = RefundWorkflow().execute_transaction(
                connection,
                context,
                request,
                capability,
                SimpleNamespace(is_tainted=False),
                SimpleNamespace(risk_level="LOW"),
                datetime.now(UTC),
                capability_token,
            )
            if hasattr(result, "decision"):
                connection.execute(text("UPDATE rof12.gate_decisions SET proposal_hash = :proposal_hash WHERE operation_id = :operation_id"), {"proposal_hash": proposal_hash, "operation_id": request.operation_id})
                if result.decision.value == "REQUIRE_APPROVAL":
                    hold_id = hashlib.sha256(f"{context.tenant_id}:{request.operation_id}".encode()).hexdigest()[:32]
                    connection.execute(text("""
                        INSERT INTO rof12.holds
                            (hold_id, tenant_id, operation_id, created_by, status, expires_at, proposal, capability_token_hash)
                        VALUES (:hold_id, :tenant_id, :operation_id, :created_by, 'OPEN', :expires_at, CAST(:proposal AS jsonb), :capability_token_hash)
                        ON CONFLICT (hold_id) DO NOTHING
                    """), {
                        "hold_id": hold_id,
                        "tenant_id": context.tenant_id,
                        "operation_id": request.operation_id,
                        "created_by": context.user_id,
                        "expires_at": datetime.now(UTC) + timedelta(minutes=15),
                        "proposal": json.dumps(payload.model_dump(), default=str),
                        "capability_token_hash": hash_capability(capability_token),
                    })
                    return JSONResponse({"decision": "REQUIRE_APPROVAL", "hold_id": hold_id, "proposal_hash": proposal_hash}, status_code=202)
                return {"decision": result.decision.value, "reasons": list(result.reasons), "proposal_hash": proposal_hash}
            return {"decision": "ALLOW", "executed": True, "proposal_hash": proposal_hash}
    except IntegrityError as exc:
        raise HTTPException(409, detail={"code": "DUPLICATE_OPERATION", "message": "operation already executed"}) from exc
    except PermissionError as exc:
        raise HTTPException(403, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail="refund execution unavailable") from exc
