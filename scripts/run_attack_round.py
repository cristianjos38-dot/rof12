#!/usr/bin/env python3
import json
import os
import uuid
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rof12.core import ROF12Round


def persist_results(results):
    database_url = os.getenv("DATABASE_OWNER_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        print("Supabase persistence: not configured; local audit chain retained")
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
                    tenant_id="tenant_001",
                    event_type="ATTACK_ROUND_DECISION",
                    actor_user_id="user_001",
                    payload={
                        "attack_id": result["attack_id"],
                        "decision": result["decision"],
                        "reason_code": result["reason_code"],
                        "sha256": result["record_hash"],
                        "test_passed": result["test_passed"],
                    },
                )
        print(f"Supabase persistence: {len(results)} decisions inserted")
        return True
    except Exception as exc:  # noqa: BLE001 - local replay remains available
        print(f"Supabase persistence failed safely: {type(exc).__name__}")
        return False

def main():
    engine = ROF12Round(ROOT / "policy/policy.json")
    results = []
    for path in sorted((ROOT / "attacks").glob("ATK-*.json")):
        attack = json.loads(path.read_text())
        result = engine.run(attack)
        result["record_hash"] = engine.audit.records[-1]["record_hash"]
        expected = attack["expected_enforcement"]
        passed = result["decision"] == expected["gate_decision"] and result["reason_code"] == expected["reason_code"]
        result["test_passed"] = passed
        results.append(result)
        print(f"{attack['attack_id']} | {result['decision']:<10} | {result['reason_code']:<34} | {'PASS' if passed else 'FAIL'}")
    out = ROOT / "artifacts"
    out.mkdir(exist_ok=True)
    (out / "attack_round_results.json").write_text(json.dumps(results, indent=2))
    (out / "audit_chain.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False)+"\n" for x in engine.audit.records))
    print(f"\nAudit chain valid: {engine.audit.verify()}")
    print(f"Results: {out / 'attack_round_results.json'}")
    print(f"Audit:   {out / 'audit_chain.jsonl'}")
    persist_results(results)
    if not all(x["test_passed"] for x in results) or not engine.audit.verify():
        raise SystemExit(1)
if __name__ == "__main__":
    main()
