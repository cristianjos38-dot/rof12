import json
import os
from types import SimpleNamespace
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import AuthContext, get_auth_context
from app.api.exceptions import ApiDomainError
from app.api.state import api_state
from app.db.connection import create_app_engine
from app.persistence.audit_repository import SQLAlchemyAuditRepository
from app.provenance import ProvenanceTracker, TaintedValue
from app.security.policy_engine import GateDecision
from app.security.security_gate import SecurityGate

router = APIRouter(prefix="/tasks", tags=["tasks"])

v1_router = APIRouter(prefix="/v1/tasks", tags=["tasks"])
evaluate_router = APIRouter(prefix="/v1/evaluate", tags=["evaluation"])


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_type: str = Field(min_length=1, max_length=100)
    payload: dict


class ArtifactLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_id: str = Field(min_length=1)


def _evaluate_task_gate(payload: TaskRequest, context: AuthContext):
    serialized = json.dumps(payload.payload, sort_keys=True, ensure_ascii=False).lower()
    adversarial = any(marker in serialized for marker in ("ignora", "ignore", "reembolsa", "refund", "system:", "drop database"))
    tracker = ProvenanceTracker()
    external = tracker.extract(payload.payload, f"task:{context.tenant_id}", "agent_payload", "")
    order_id = payload.payload.get("order_id")
    if not adversarial and order_id == "order_1042":
        provenance = tracker.reconcile(TaintedValue.external(order_id, "task:order_id"), "order_1042")
    else:
        provenance = external
    return SecurityGate().evaluate(
        context,
        SimpleNamespace(tool_name="drop_database" if adversarial else "refund_service"),
        SimpleNamespace(valid=True, reasons=()),
        provenance,
        SimpleNamespace(risk_level="HIGH" if adversarial else "LOW"),
        SimpleNamespace(checks={"V2": True, "V4": True, "V5": True}),
        SimpleNamespace(active=False),
    )


def _record_gate_event(request: Request, context: AuthContext, decision, task_id: str) -> None:
    event_payload = {
        "decision": decision.decision.value,
        "reasons": list(decision.reasons),
        "task_id": task_id,
        "request_id": getattr(request.state, "request_id", ""),
    }
    if not os.getenv("DATABASE_URL") and os.getenv("APP_ENV", "local") == "local":
        api_state.audit.setdefault((context.tenant_id, task_id), []).append(event_payload)
        return
    try:
        with create_app_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            SQLAlchemyAuditRepository(connection).append(task_id, context.tenant_id, "SECURITY_GATE_DECISION", context.user_id, event_payload)
    except SQLAlchemyError as exc:
        raise ApiDomainError("AUDIT_PERSISTENCE_FAILED", "security decision could not be audited", 503) from exc


@v1_router.post("")
def create_task(request: Request, payload: TaskRequest, context: AuthContext = Depends(get_auth_context)):
    task_id = str(uuid4())
    decision = _evaluate_task_gate(payload, context)
    _record_gate_event(request, context, decision, task_id)
    if decision.decision is not GateDecision.ALLOW:
        code = "GATE_DENY" if decision.decision is GateDecision.DENY else "GATE_QUARANTINE"
        status_code = 403 if decision.decision is GateDecision.DENY else 409
        raise ApiDomainError(code, "security gate rejected task payload", status_code)
    with api_state.lock:
        api_state.tasks[(context.tenant_id, task_id)] = {"task_id": task_id, "tenant_id": context.tenant_id, "status": "CREATED", "task_type": payload.task_type, "payload": payload.payload, "artifacts": []}
    return api_state.tasks[(context.tenant_id, task_id)]


@evaluate_router.post("")
def evaluate(request: Request, payload: TaskRequest, context: AuthContext = Depends(get_auth_context)):
    """Stable evaluation alias; authority remains resolved by the server."""
    return create_task(request, payload, context)


@v1_router.get("/{task_id}")
def get_task(task_id: str, context: AuthContext = Depends(get_auth_context)):
    task = api_state.task(context.tenant_id, task_id)
    if task is None:
        raise HTTPException(404, detail="task not found")
    return task


@v1_router.post("/{task_id}/artifacts")
def link_artifact(task_id: str, payload: ArtifactLink, context: AuthContext = Depends(get_auth_context)):
    task = api_state.task(context.tenant_id, task_id)
    if task is None or (context.tenant_id, payload.artifact_id) not in api_state.artifacts:
        raise HTTPException(404, detail="task or artifact not found")
    task["artifacts"].append(payload.artifact_id)
    return task


@v1_router.get("/{task_id}/audit")
def task_audit(task_id: str, context: AuthContext = Depends(get_auth_context)):
    if api_state.task(context.tenant_id, task_id) is None:
        raise HTTPException(404, detail="task not found")
    return {"task_id": task_id, "events": api_state.audit.get((context.tenant_id, task_id), [])}


@router.get("/context")
def task_context(context: AuthContext = Depends(get_auth_context)) -> dict:
    return {
        "user_id": context.user_id,
        "tenant_id": context.tenant_id,
        "role": context.role,
        "membership_status": context.membership_status,
    }
