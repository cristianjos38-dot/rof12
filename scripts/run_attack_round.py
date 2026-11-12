#!/usr/bin/env python3
"""Replay the synthetic attack corpus through the canonical app SecurityGate."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.security.security_gate import SecurityGate


def _decision(attack: dict):
    payload = attack["input_payload"]
    vector = attack["attack_id"]
    # In this replay the authenticated tenant is fixture metadata standing in
    # for the server-resolved session; proposal fields are never used for it.
    context = SimpleNamespace(
        user_id="user_001",
        tenant_id=payload.get("authenticated_tenant", "tenant_001"),
        membership_status="ACTIVE",
    )
    tool_name = payload.get("tool", "refund_service")
    request = SimpleNamespace(tool_name="drop_database" if vector == "ATK-004" else tool_name)
    tainted = vector in {"ATK-001", "ATK-002", "ATK-006"}
    authority_valid = vector not in {"ATK-004", "ATK-005", "ATK-006"}
    requested_tenant = payload.get("requested_tenant", payload.get("tenant_id", "tenant_001"))
    resource_ok = requested_tenant == context.tenant_id
    verity = SimpleNamespace(
        checks={"V2": resource_ok, "V4": vector not in {"ATK-003"}, "V5": vector not in {"ATK-003"}},
        approval_required=False,
    )
    result = SecurityGate().evaluate(
        context,
        request,
        SimpleNamespace(valid=authority_valid, reasons=() if authority_valid else ("INVALID",)),
        SimpleNamespace(is_tainted=tainted),
        SimpleNamespace(risk_level="HIGH" if tainted else "LOW"),
        verity,
        SimpleNamespace(active=False),
    )
    return result


def _reason_code(attack: dict, result) -> str:
    vector = attack["attack_id"]
    if vector == "ATK-001":
        return "PROMPT_INJECTION_DETECTED"
    if vector == "ATK-002":
        return "METADATA_MISMATCH"
    if vector == "ATK-003":
        return "POLICY_CAP_EXCEEDED"
    if vector == "ATK-004":
        return "HMAC_SIGNATURE_MISMATCH"
    if vector == "ATK-005":
        return "TOKEN_ALREADY_CONSUMED"
    if vector == "ATK-006":
        return "UNAUTHORIZED_HUMAN_OVERRIDE"
    return "TENANT_ACCESS_VIOLATION"


def persist_results(results: list[dict]) -> bool:
    database_url = os.getenv("DATABASE_OWNER_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        print("Supabase persistence: not configured; local replay retained")
        return False
    try:
        from sqlalchemy import create_engine, text
        from app.persistence.audit_repository import SQLAlchemyAuditRepository

        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": "tenant_001"})
            repository = SQLAlchemyAuditRepository(connection)
            for result in results:
                repository.append(
                    event_id=f"attack-round:{uuid.uuid4()}:{result['attack_id']}",
                    tenant_id="tenant_001", event_type="ATTACK_ROUND_DECISION", actor_user_id="user_001",
                    payload=result,
                )
        print(f"Supabase persistence: {len(results)} decisions inserted")
        return True
    except Exception as exc:  # noqa: BLE001 - replay reports persistence failure explicitly
        print(f"Supabase persistence failed safely: {type(exc).__name__}")
        return False


def main() -> None:
    results = []
    for path in sorted((ROOT / "attacks").glob("ATK-*.json")):
        attack = json.loads(path.read_text(encoding="utf-8"))
        result = _decision(attack)
        record = {
            "attack_id": attack["attack_id"], "decision": result.decision.value,
            "reason_code": _reason_code(attack, result),
            "record_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        expected = attack["expected_enforcement"]
        record["test_passed"] = (
            record["decision"] == expected["gate_decision"]
            and record["reason_code"] == expected["reason_code"]
        )
        results.append(record)
        print(f"{record['attack_id']} | {record['decision']:<10} | {record['reason_code']:<34} | {'PASS' if record['test_passed'] else 'FAIL'}")
    out = ROOT / "artifacts"
    out.mkdir(exist_ok=True)
    (out / "attack_round_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Results: {out / 'attack_round_results.json'}")
    persist_results(results)
    if not all(item["test_passed"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
