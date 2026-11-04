"""n8n Gmail/PDF bridge for the canonical ROF12 application."""
from __future__ import annotations

import hashlib
import json
import re
import threading
from types import SimpleNamespace
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.state import api_state
from app.config import APP_ENV
from app.db.connection import create_app_engine
from app.persistence.audit_logger import chain_hash
from app.persistence.audit_repository import SQLAlchemyAuditRepository
from app.provenance import TaintedValue
from app.security.policy_engine import GateDecision
from app.security.security_gate import SecurityGate
from rof12.adapters.voice_adapter import speak

router = APIRouter(prefix="/v1/n8n", tags=["n8n"])
_audit_lock = threading.RLock()

ALLOW_MESSAGE = "Documento verificado por SecurityGate. Procediendo con el agente."
DENY_MESSAGE = "Alerta de seguridad. Ataque detectado en correo. Agente detenido."
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
    tenant_id: str = Field(default="tenant_001", min_length=1, max_length=128)
    agent_id: str = Field(default="gmail_invoicing_agent", min_length=1, max_length=128)


def _speak_async(message: str) -> None:
    threading.Thread(target=speak, args=(message,), name="rof12-n8n-voice", daemon=True).start()


def _find_threats(document_text: str) -> list[dict[str, str]]:
    findings = []
    for code, pattern in THREATS:
        match = pattern.search(document_text)
        if match:
            findings.append({"code": code, "evidence": match.group(0)[:160]})
    return findings


def _evaluate_gate(payload: InspectEmailRequest, findings: list[dict[str, str]]):
    """Run the canonical SecurityGate with a non-mutating inspection context."""
    context = SimpleNamespace(user_id="user_001", tenant_id=payload.tenant_id, membership_status="ACTIVE")
    request = SimpleNamespace(tool_name="refund_service")
    capability = SimpleNamespace(valid=True, reasons=())
    provenance = TaintedValue.trusted(payload.document_text, f"n8n:{hashlib.sha256(payload.document_text.encode()).hexdigest()}")
    risk = SimpleNamespace(risk_level="HIGH" if findings else "LOW")
    verity = SimpleNamespace(checks={"V2": True, "V4": True, "V5": True}, approval_required=False)
    system_state = SimpleNamespace(active=False)
    result = SecurityGate().evaluate(context, request, capability, provenance, risk, verity, system_state)
    if findings:
        return GateDecision.DENY, tuple(item["code"] for item in findings), result
    return result.decision, result.reasons, result


def _local_audit(event_id: str, tenant_id: str, payload: dict) -> str:
    with _audit_lock:
        records = api_state.audit.setdefault((tenant_id, "n8n-email-inspection"), [])
        previous = records[-1]["event_hash"] if records else "GENESIS"
        event = {"event_id": event_id, "tenant_id": tenant_id, "event_type": "N8N_EMAIL_INSPECTION",
                 "actor_user_id": "user_001", "payload": payload}
        digest = chain_hash(previous, event)
        records.append({**event, "prev_hash": previous, "event_hash": digest})
        return digest


def _audit(request: Request, payload: InspectEmailRequest, event: dict) -> str:
    event_id = event["event_id"]
    if APP_ENV == "local" and not __import__("os").getenv("DATABASE_URL"):
        return _local_audit(event_id, payload.tenant_id, event)
    try:
        with create_app_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": payload.tenant_id})
            result = SQLAlchemyAuditRepository(connection).append(
                event_id, payload.tenant_id, "N8N_EMAIL_INSPECTION", "user_001", event
            )
            return result.event_hash
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="security decision could not be persisted") from exc


@router.post("/inspect-email")
def inspect_email(payload: InspectEmailRequest, request: Request):
    document_hash = hashlib.sha256(payload.document_text.encode("utf-8")).hexdigest()
    findings = _find_threats(payload.document_text)
    decision, gate_reasons, gate_result = _evaluate_gate(payload, findings)
    if decision is GateDecision.ALLOW:
        permit_token = None
        alert_message = ""
        _speak_async(ALLOW_MESSAGE)
    else:
        permit_token = None
        alert_message = DENY_MESSAGE
        _speak_async(DENY_MESSAGE)
    reasons = list(dict.fromkeys([*gate_reasons, *(item["code"] for item in findings)]))
    event = {
        "event_id": str(uuid4()), "sender": payload.sender, "subject": payload.subject,
        "agent_id": payload.agent_id, "document_sha256": document_hash,
        "decision": decision.value, "reasons": reasons,
        "threat_detected": findings or None, "gate_dimensions": getattr(gate_result, "dimensions", {}),
        "request_id": getattr(request.state, "request_id", ""),
    }
    event_hash = _audit(request, payload, event)
    return {
        "is_safe": decision is GateDecision.ALLOW,
        "decision": "ALLOW" if decision is GateDecision.ALLOW else "DENY",
        "reasons": reasons,
        "threat_detected": findings or None,
        "permit_token": permit_token,
        "sha256": event_hash,
        "alert_message": alert_message,
    }
