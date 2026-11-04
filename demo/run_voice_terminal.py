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
sys.path.insert(0, str(ROOT))

from rof12.adapters.voice_adapter import (  # noqa: E402
    approval_from_text,
    DEFAULT_VOICE,
    listen_text,
    speak,
    speak_decision,
)
from rof12.meta_client import MetaClient  # noqa: E402
from rof12.audit import Audit  # noqa: E402
from rof12.gate import Gate, Proposal  # noqa: E402
from rof12.tools import Store, ToolRuntime  # noqa: E402


def _load_policy() -> dict:
    return json.loads((ROOT / "rof12-demo" / "policy" / "policy.json").read_text(encoding="utf-8"))


def _is_exit_command(text: str) -> bool:
    normalized = text.casefold()
    return any(word in normalized for word in ("apágate", "apag ate", "cerrar", "salir", "apagar", "adiós", "adios", "exit"))


def _canonical_tool(tool_name: str) -> str:
    """Map only known refund aliases to the registered Gate capability."""
    normalized = tool_name.strip().casefold().replace("-", "_")
    if normalized in {"process_refund", "refund", "refund_create", "create_refund", "refunds_create"} or "refund" in normalized or "reembolso" in normalized:
        return "refunds.create"
    return tool_name


def _persist_supabase(event_type: str, tenant_id: str, payload: dict) -> bool:
    """Persist a sanitized decision when a database URL is configured."""
    url = os.getenv("DATABASE_OWNER_URL") or os.getenv("DATABASE_URL")
    if not url:
        return False
    try:
        from sqlalchemy import create_engine, text
        from app.persistence.audit_repository import SQLAlchemyAuditRepository

        engine = create_engine(url, pool_pre_ping=True)
        with engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})
            SQLAlchemyAuditRepository(connection).append(
                event_id=f"voice:{uuid.uuid4()}",
                tenant_id=tenant_id,
                event_type=event_type,
                actor_user_id="user_001",
                payload=payload,
            )
        return True
    except Exception as exc:  # noqa: BLE001 - local demo must retain keyboard/local audit fallback
        print(f"[LOCAL AUDIT] Supabase no disponible; traza local conservada ({type(exc).__name__})")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="ROF12 voice terminal")
    parser.add_argument("--keyboard", action="store_true", help="usar teclado sin intentar micrófono")
    parser.add_argument("--listen", action="store_true", help="habilitar captura de micrófono explícitamente")
    parser.add_argument(
        "--voice",
        nargs="?",
        const=DEFAULT_VOICE,
        default=None,
        help="habilitar micrófono y elegir voz Edge-TTS (por defecto, teclado seguro)",
    )
    parser.add_argument("--no-speech", action="store_true", help="no invocar say; útil para pruebas")
    parser.add_argument("--audit-path", default=str(ROOT / "rof12-demo" / "out" / "voice_audit.jsonl"))
    args = parser.parse_args()

    audit = Audit(args.audit_path)
    store = Store()
    gate = Gate(_load_policy(), store, audit)
    runtime = ToolRuntime(store, gate.verify_permit)
    meta = MetaClient()
    voice_name = args.voice or DEFAULT_VOICE
    voice_enabled = bool((args.listen or args.voice) and not args.keyboard)
    session_id = f"voice-{uuid.uuid4()}"
    empty_voice_attempts = 0
    print("ROF12 Voice Terminal — la voz propone; SecurityGate decide.")
    print("Ejemplo: reembolsa Q45.00 en la orden ORD-7731. Ctrl-D para salir.")

    def get_text(prompt: str) -> str:
        nonlocal voice_enabled, empty_voice_attempts
        if args.keyboard or not voice_enabled:
            text = input(prompt + (" [teclado] " if not args.keyboard else ""))
            if not args.keyboard and text.strip().casefold() in {"", "v"}:
                voice_enabled = True
                empty_voice_attempts = 0
                print("[MICRÓFONO REACTIVADO]")
                return ""
            return text
        print(prompt + " [micrófono]")
        return listen_text(timeout=30.0)

    def announce(decision: str, codes=None) -> None:
        if not args.no_speech:
            speak_decision(decision, lambda message: speak(message, voice_name), codes=codes)

    while True:
        try:
            command = get_text("\nComando> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            return 0
        except RuntimeError as exc:
            empty_voice_attempts += 1
            print(f"[VOICE NOTICE] {exc}")
            if not args.no_speech:
                speak("No logré escucharte, por favor repite tu instrucción.", voice_name)
            if empty_voice_attempts >= 2:
                voice_enabled = False
                print("[MODO TECLADO ACTIVO] Presiona [Espacio] o escribe 'v' para reactivar el micrófono.")
            continue
        if not command:
            continue
        if _is_exit_command(command):
            print("Cerrando runtime ROF12. Sesión finalizada.")
            if not args.no_speech:
                speak("Cerrando runtime ROF12. Sesión finalizada.", voice_name)
            sys.exit(0)
        try:
            response = meta.respond(command)
            label = "Live" if response.source == "meta" else "Mock"
            print(f"[Meta AI {label}] tokens={response.tokens_total} latency={response.latency_ms}ms")
            if response.mode == "conversation":
                record = audit.append("conversation", response.text, source=response.source, input_text=command)
                print(f"ROF12: {response.text}")
                if response.text and not args.no_speech:
                    speak(response.text, voice_name)
                persisted = _persist_supabase(
                    "VOICE_CONVERSATION",
                    "tenant_001",
                    {"text": response.text, "source": response.source, "audit_hash": record["hash"]},
                )
                print(f"Audit SHA-256: {record['hash']} · Supabase={'OK' if persisted else 'no configurado'}")
                continue

            proposal_data = response.proposal
            tool_name = proposal_data.get("tool_name") or proposal_data.get("tool") or "unrecognized.action"
            tool_name = _canonical_tool(tool_name)
            args_data = proposal_data.get("args", {})
            proposal = Proposal("TKT-1042", "support-agent-01", tool_name, args_data, command, tenant_id="tenant_001")
            decision = gate.evaluate(proposal)
            event_hash = audit.records()[-1]["hash"]
            print(f"Meta [{response.source}] → Gate: {decision.decision} codes={decision.codes or ['-']} sha256={event_hash}")
            announce(decision.decision, decision.codes)
            if decision.hold_id:
                answer = get_text("Respuesta (autorizar/cancelar)> ")
                approved = approval_from_text(answer, decision.hold_id)
                approver_id = f"voice-supervisor:{session_id}"
                gate.decide_hold(decision.hold_id, approved, approver_id, answer, supervisor_session=session_id)
                print(f"Hold {decision.hold_id}: confirmación explícita={'sí' if approved else 'no'}; supervisor_session={session_id}")
                if approved:
                    decision = gate.resume(decision.hold_id, proposal)
                    print(f"Revalidación: {decision.decision} codes={decision.codes or ['-']}")
                    announce(decision.decision, decision.codes)
            if decision.decision == "ALLOW" and decision.permit:
                result = gate.execute(runtime, proposal, decision.permit)
                print(f"Ejecución: {result}")
            persisted = _persist_supabase(
                "VOICE_SECURITY_DECISION",
                proposal.tenant_id,
                {"decision": decision.decision, "codes": decision.codes, "proposal_hash": proposal.hash, "audit_hash": event_hash, "tool": proposal.tool},
            )
            print(f"Audit SHA-256: {event_hash} · Supabase={'OK' if persisted else 'no configurado'}")
        except (AttributeError, TypeError, KeyError, ValueError) as exc:
            # A malformed model proposal is still denied and audited; it is not
            # rejected by a pre-parser or silently discarded.
            proposal = Proposal("TKT-1042", "support-agent-01", "unrecognized.action", {}, command, tenant_id="tenant_001")
            decision = gate.evaluate(proposal)
            print(f"Meta proposal inválida → Gate: {decision.decision} ({type(exc).__name__})")
            announce(decision.decision, decision.codes)


if __name__ == "__main__":
    raise SystemExit(main())
