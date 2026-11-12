"""n8n Gmail/PDF bridge with server-owned identity and fail-closed evaluation."""
from __future__ import annotations

import hashlib
import re
import threading
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import AuthContext, get_auth_context
from app.api.state import api_state
from app.config import APP_ENV
from app.db.connection import create_app_engine
from app.persistence.audit_logger import chain_hash
from app.persistence.audit_repository import SQLAlchemyAuditRepository
from app.provenance import TaintedValue
from app.security.kill_switch import KillSwitch
from app.security.policy_engine import GateDecision
from app.security.security_gate import SecurityGate

router = APIRouter(prefix="/v1/n8n", tags=["n8n"])
_audit_lock = threading.RLock()

ALLOW_MESSAGE = "Document accepted by the SecurityGate."
DENY_MESSAGE = "Security alert. The email was blocked."
THREATS = (
    ("PROMPT_INJECTION", re.compile(r"system\s+override|ignore\s+(all\s+)?instructions|ignora\s+(las\s+)?instrucciones|nueva\s+directiva|override\s+(the\s+)?policy", re.I)),
    ("FINANCIAL_MANIPULATION", re.compile(r"transferir|transfer\s+funds?|billetera|wallet|wire\s+money|change\s+bank|cambiar\s+cuenta|ejecutar\s+ahora", re.I)),
    ("EXFILTRATION_OR_ESCAPE", re.compile(r"reveal\s+(secrets|system)|exfiltrat|bypass|desactiva\s+la\s+seguridad|ignore\s+safety", re.I)),
    ("INVISIBLE_TEXT", re.compile(r"[\u200b\u200c\u200d\u2060\u2066\u2067\u2068\u2069\ufeff]")),
)


class InspectEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sender: str = Field(min_length=1, max_length=320)
    subject: str = Field(min_length=1, max_length=998)
    document_text: str = Field(min_length=1)
    agent_id: str = Field(default="gmail_invoicing_agent", min_length=1, max_length=128)


def _find_threats(document_text: str) -> list[dict[str, str]]:
    findings = []
    for code, pattern in THREATS:
        match = pattern.search(document_text)
        if match:
            findings.append({"code": code, "evidence": match.group(0)[:160]})
    return findings


def _find_order_id(document_text: str) -> str | None:
    match = re.search(r"\b(order[_ -]?\d{3,}|ord[-_]\d{3,})\b", document_text, re.I)
    return match.group(1).lower().replace("-", "_") if match else None


def _evaluate_gate(payload: InspectEmailRequest, findings: list[dict[str, str]], context: AuthContext):
    order_id = _find_order_id(payload.document_text)
    if not order_id:
        return (GateDecision.DENY if findings else GateDecision.ALLOW, tuple(item["code"] for item in findings), None, "heuristic")
    if not __import__("os").getenv("DATABASE_URL"):
        return (GateDecision.DENY, ("DATABASE_NOT_CONFIGURED",), None, "heuristic")
    try:
        from app.domain.contracts import ToolRequest
        from app.verification.verityflow import evaluate_snapshot

        request = ToolRequest(
            order_id=order_id,
            amount=__import__("decimal").Decimal("0.01"),
            reason="n8n inspection",
            operation_id=f"n8n-{hashlib.sha256(payload.document_text.encode()).hexdigest()[:24]}",
        )
        with create_app_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            order = connection.execute(text("""
                SELECT tenant_id, owner_user_id, status, refundable_balance
                  FROM rof12.orders WHERE order_id = :order_id
            """), {"order_id": order_id}).mappings().first()
            system_state = KillSwitch().read(connection)
        ctx = SimpleNamespace(tenant_id=context.tenant_id, user_id=context.user_id)
        verity = evaluate_snapshot(dict(order) if order else None, request, ctx, None, False, datetime.now(UTC))
        result = SecurityGate().evaluate(
            context,
            SimpleNamespace(tool_name="refund_service"),
            SimpleNamespace(valid=False, reasons=("CAPABILITY_NOT_FOUND",)),
            TaintedValue.external(payload.document_text, f"n8n:{hashlib.sha256(payload.document_text.encode()).hexdigest()}"),
            SimpleNamespace(risk_level="HIGH" if findings else "LOW"),
            verity,
            system_state,
        )
        return result.decision, tuple(dict.fromkeys([*result.reasons, *(item["code"] for item in findings)])), result, "postgres_verityflow"
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="n8n evaluation could not be completed") from exc


def _local_audit(event_id: str, tenant_id: str, actor_user_id: str, payload: dict) -> str:
    with _audit_lock:
        records = api_state.audit.setdefault((tenant_id, "n8n-email-inspection"), [])
        previous = records[-1]["event_hash"] if records else "GENESIS"
        event = {"event_id": event_id, "tenant_id": tenant_id, "event_type": "N8N_EMAIL_INSPECTION", "actor_user_id": actor_user_id, "payload": payload}
        digest = chain_hash(previous, event)
        records.append({**event, "prev_hash": previous, "event_hash": digest})
        return digest


def _audit(request: Request, context: AuthContext, event: dict) -> str:
    if APP_ENV == "local" and not __import__("os").getenv("DATABASE_URL"):
        return _local_audit(event["event_id"], context.tenant_id, context.user_id, event)
    try:
        with create_app_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            result = SQLAlchemyAuditRepository(connection).append(
                event["event_id"], context.tenant_id, "N8N_EMAIL_INSPECTION", context.user_id, event
            )
            return result.event_hash
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="security decision could not be persisted") from exc


@router.post("/inspect-email")
def inspect_email(payload: InspectEmailRequest, request: Request, context: AuthContext = Depends(get_auth_context)):
    document_hash = hashlib.sha256(payload.document_text.encode("utf-8")).hexdigest()
    findings = _find_threats(payload.document_text)
    decision, gate_reasons, gate_result, evaluation_source = _evaluate_gate(payload, findings, context)
    reasons = list(dict.fromkeys([*gate_reasons, *(item["code"] for item in findings)]))
    event = {
        "event_id": str(uuid4()),
        "sender": payload.sender,
        "subject": payload.subject,
        "agent_id": payload.agent_id,
        "document_sha256": document_hash,
        "decision": decision.value,
        "reasons": reasons,
        "threat_detected": findings or None,
        "gate_dimensions": getattr(gate_result, "dimensions", {}),
        "evaluation_source": evaluation_source,
        "request_id": getattr(request.state, "request_id", ""),
    }
    event_hash = _audit(request, context, event)
    allowed = decision is GateDecision.ALLOW
    return {
        "is_safe": allowed,
        "decision": "ALLOW" if allowed else "DENY",
        "reasons": reasons,
        "threat_detected": findings or None,
        "sha256": event_hash,
        "evaluation_source": evaluation_source,
        "alert_message": ALLOW_MESSAGE if allowed else DENY_MESSAGE,
        "document_text": payload.document_text if allowed else None,
        "sender": payload.sender if allowed else None,
        "subject": payload.subject if allowed else None,
    }
