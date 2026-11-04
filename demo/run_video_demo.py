#!/usr/bin/env python3
"""Interactive ATK-001..ATK-007 demo with optional Supabase persistence."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rof12.core import ROF12Round  # noqa: E402
sys.path.insert(0, str(ROOT))
_voice_spec = importlib.util.spec_from_file_location("rof12_voice_adapter", ROOT / "rof12" / "adapters" / "voice_adapter.py")
_voice_module = importlib.util.module_from_spec(_voice_spec)
sys.modules[_voice_spec.name] = _voice_module
_voice_spec.loader.exec_module(_voice_module)
speak_decision = _voice_module.speak_decision


def _database_url() -> str | None:
    return os.getenv("DATABASE_OWNER_URL") or os.getenv("DATABASE_URL")


def check_db_connection() -> bool:
    """Return whether the configured Supabase/local PostgreSQL responds."""
    url = _database_url()
    if not url:
        return False
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - health probe must not crash the demo
        return False


def persist_events(results: list[dict]) -> bool:
    url = _database_url()
    if not url:
        return False
    try:
        from sqlalchemy import create_engine, text
        from app.persistence.audit_repository import SQLAlchemyAuditRepository

        engine = create_engine(url, pool_pre_ping=True)
        with engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": "tenant_001"})
            repository = SQLAlchemyAuditRepository(connection)
            for result in results:
                repository.append(
                    event_id=f"video-demo:{uuid.uuid4()}:{result['attack_id']}",
                    tenant_id="tenant_001",
                    event_type="VIDEO_ATTACK_DECISION",
                    actor_user_id="user_001",
                    payload={
                        "attack_id": result["attack_id"],
                        "decision": result["decision"],
                        "reason_code": result["reason_code"],
                        "content_sha256": result["record_hash"],
                    },
                )
        return True
    except Exception as exc:  # noqa: BLE001 - retain local demo on DB failure
        print(f"Supabase persistence unavailable: {type(exc).__name__}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="ROF12 attack round video demo")
    parser.add_argument("--interactive", action="store_true", help="pause before each attack")
    parser.add_argument("--no-speech", action="store_true", help="disable audio for CI")
    args = parser.parse_args()

    engine = ROF12Round(ROOT / "policy" / "policy.json")
    results = []
    paths = sorted((ROOT / "attacks").glob("ATK-*.json"))
    for path in paths:
        if args.interactive:
            input(f"\nPresiona Enter para evaluar {path.stem}...")
        attack = json.loads(path.read_text(encoding="utf-8"))
        result = engine.run(attack)
        result["record_hash"] = engine.audit.records[-1]["record_hash"]
        results.append(result)
        expected = attack["expected_enforcement"]
        passed = result["decision"] == expected["gate_decision"] and result["reason_code"] == expected["reason_code"]
        print(f"{attack['attack_id']} | {result['decision']:<10} | {result['reason_code']:<34} | {'PASS' if passed else 'FAIL'}")
        if not args.no_speech:
            speak_decision(result["decision"], codes=[result["reason_code"]])

    print(f"Audit chain valid: {engine.audit.verify()}")
    if persist_events(results):
        print("Supabase hash confirmation: persisted in rof12.audit_events (OK)")
    else:
        print("Supabase hash confirmation: local-only replay")
    all_passed = all(
        result["decision"] == json.loads(path.read_text(encoding="utf-8"))["expected_enforcement"]["gate_decision"]
        and result["reason_code"] == json.loads(path.read_text(encoding="utf-8"))["expected_enforcement"]["reason_code"]
        for result, path in zip(results, paths)
    )
    return 0 if all_passed and engine.audit.verify() else 1


if __name__ == "__main__":
    raise SystemExit(main())
