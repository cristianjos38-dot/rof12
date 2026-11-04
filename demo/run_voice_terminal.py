#!/usr/bin/env python3
"""Interactive voice/keyboard terminal for the local ROF12 SecurityGate demo."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rof12-demo"))
sys.path.insert(0, str(ROOT))

from rof12.adapters.voice_adapter import (  # noqa: E402
    approval_from_text,
    DEFAULT_VOICE,
    listen_text,
    parse_command,
    parse_proposal,
    INVALID_COMMAND_MESSAGE,
    speak,
    speak_decision,
)
from rof12.audit import Audit  # noqa: E402
from rof12.gate import Gate, Proposal  # noqa: E402
from rof12.tools import Store, ToolRuntime  # noqa: E402


def _load_policy() -> dict:
    return json.loads((ROOT / "rof12-demo" / "policy" / "policy.json").read_text(encoding="utf-8"))


def _persist_supabase(decision, proposal, audit_hash: str) -> bool:
    """Persist a sanitized decision when a database URL is configured."""
    url = os.getenv("DATABASE_OWNER_URL") or os.getenv("DATABASE_URL")
    if not url:
        return False
    try:
        from sqlalchemy import create_engine, text
        from app.persistence.audit_repository import SQLAlchemyAuditRepository

        engine = create_engine(url, pool_pre_ping=True)
        with engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": proposal.tenant_id})
            SQLAlchemyAuditRepository(connection).append(
                event_id=f"voice:{uuid.uuid4()}",
                tenant_id=proposal.tenant_id,
                event_type="VOICE_SECURITY_DECISION",
                actor_user_id="user_001",
                payload={
                    "decision": decision.decision,
                    "proposal_hash": proposal.hash,
                    "audit_hash": audit_hash,
                    "tool": proposal.tool,
                },
            )
        return True
    except Exception as exc:  # noqa: BLE001 - local demo must retain keyboard/local audit fallback
        print(f"[LOCAL AUDIT] Supabase no disponible; traza local conservada ({type(exc).__name__})")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="ROF12 voice terminal")
    parser.add_argument("--keyboard", action="store_true", help="usar teclado sin intentar micrófono")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="voz Edge-TTS; fallback macOS say")
    parser.add_argument("--no-speech", action="store_true", help="no invocar say; útil para pruebas")
    parser.add_argument("--audit-path", default=str(ROOT / "rof12-demo" / "out" / "voice_audit.jsonl"))
    args = parser.parse_args()

    audit = Audit(args.audit_path)
    store = Store()
    gate = Gate(_load_policy(), store, audit)
    runtime = ToolRuntime(store, gate.verify_permit)
    print("ROF12 Voice Terminal — la voz propone; SecurityGate decide.")
    print("Ejemplo: reembolsa Q45.00 en la orden ORD-7731. Ctrl-D para salir.")

    def get_text(prompt: str) -> str:
        if args.keyboard:
            return input(prompt)
        try:
            print(prompt + " [micrófono]")
            return listen_text()
        except (RuntimeError, EOFError) as exc:
            print(f"[KEYBOARD FALLBACK] {exc}")
            return input(prompt + " [teclado] ")

    def announce(decision: str, codes=None) -> None:
        if not args.no_speech:
            speak_decision(decision, lambda message: speak(message, args.voice), codes=codes)

    def announce_invalid() -> None:
        print("Uso: reembolsa Q45.00 en la orden ORD-7731 con motivo de disputa.")
        print("También acepta: reembolsar $45, devolver USD 45, procesar reembolso 45 EUR.")
        if not args.no_speech:
            speak(INVALID_COMMAND_MESSAGE, args.voice)

    while True:
        try:
            command = get_text("\nComando> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            return 0
        if not command:
            continue
        try:
            spoken = parse_proposal(command)
            proposal = Proposal(
                spoken.task_id, spoken.agent, spoken.tool, spoken.args, spoken.rationale, tenant_id=spoken.tenant_id
            )
            decision = gate.evaluate(proposal)
            event_hash = audit.records()[-1]["hash"]
            print(f"Gate: {decision.decision} codes={decision.codes or ['-']} sha256={event_hash}")
            announce(decision.decision, decision.codes)
            if decision.hold_id:
                answer = get_text("Respuesta (autorizar/cancelar)> ")
                approved = approval_from_text(answer)
                gate.decide_hold(decision.hold_id, approved, "voice-operator", answer)
                if approved:
                    decision = gate.resume(decision.hold_id, proposal)
                    print(f"Revalidación: {decision.decision} codes={decision.codes or ['-']}")
                    announce(decision.decision, decision.codes)
            if decision.decision == "ALLOW" and decision.permit:
                result = gate.execute(runtime, proposal, decision.permit)
                print(f"Ejecución: {result}")
            persisted = _persist_supabase(decision, proposal, event_hash)
            print(f"Audit SHA-256: {event_hash} · Supabase={'OK' if persisted else 'no configurado'}")
        except ValueError as exc:
            print(f"[INPUT REJECTED] {exc}")
            print(INVALID_COMMAND_MESSAGE)
            announce_invalid()


if __name__ == "__main__":
    raise SystemExit(main())
