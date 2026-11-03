from __future__ import annotations

import argparse
import json
import os
import time
from uuid import uuid4

from sqlalchemy import create_engine, text

from app.persistence.audit_repository import SQLAlchemyAuditRepository
from demo.baseline import run as run_baseline
from demo.common import load_fixtures
from demo.protected import run as run_protected

CREATE_RESULTS = """
CREATE TABLE IF NOT EXISTS rof12.demo_results (
    run_id TEXT NOT NULL,
    fixture_id TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('BASELINE', 'PROTECTED')),
    disposition TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'ALLOW',
    risk_level TEXT NOT NULL,
    signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    meta_trace JSONB NOT NULL DEFAULT '{}'::jsonb,
    latency_ms NUMERIC(12, 3) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, fixture_id, mode)
)
"""


def persist_and_read(rows: list[dict], database_url: str, run_id: str) -> list[dict]:
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text(CREATE_RESULTS))
        connection.execute(text("ALTER TABLE rof12.demo_results ADD COLUMN IF NOT EXISTS latency_ms NUMERIC(12, 3) NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE rof12.demo_results ADD COLUMN IF NOT EXISTS decision TEXT NOT NULL DEFAULT 'ALLOW'"))
        connection.execute(text("ALTER TABLE rof12.demo_results ADD COLUMN IF NOT EXISTS meta_trace JSONB NOT NULL DEFAULT '{}'::jsonb"))
        for row in rows:
            connection.execute(
                text("""
                    INSERT INTO rof12.demo_results
                        (run_id, fixture_id, sha256, mode, disposition, decision, risk_level, signals, meta_trace, latency_ms)
                    VALUES (:run_id, :fixture_id, :sha256, :mode, :disposition, :decision, :risk_level, CAST(:signals AS jsonb), CAST(:meta_trace AS jsonb), :latency_ms)
                """),
                {**row, "run_id": run_id, "signals": json.dumps(row["signals"]), "meta_trace": json.dumps(row["meta_trace"])},
            )
            if row["mode"] == "PROTECTED":
                SQLAlchemyAuditRepository(connection).append(
                    event_id=f"demo:{run_id}:{row['fixture_id']}",
                    tenant_id="tenant_001",
                    event_type="DEMO_SECURITY_DECISION",
                    actor_user_id="user_001",
                    payload={
                        "run_id": run_id,
                        "fixture_id": row["fixture_id"],
                        "decision": row["decision"],
                        "risk_level": row["risk_level"],
                        "content_sha256": row["sha256"],
                        "meta_trace": row["meta_trace"],
                    },
                )
        result = connection.execute(
            text("""
                SELECT fixture_id, sha256, mode, disposition, decision, risk_level, signals, latency_ms
                FROM rof12.demo_results
                WHERE run_id = :run_id
                ORDER BY fixture_id, mode
            """),
            {"run_id": run_id},
        ).mappings()
        return [dict(row) for row in result]


def print_recording_table(rows: list[dict], run_id: str) -> None:
    print("ROF12 — BASELINE vs PROTECTED")
    print(f"run_id: {run_id}")
    print("=" * 96)
    for row in rows:
        label = "[BASELINE: VULNERABLE]" if row["mode"] == "BASELINE" else (
            "[PROTECTED: BLOCKED]" if row["decision"] in {"DENY", "QUARANTINE"} else "[PROTECTED: ALLOW]"
        )
        signals = ",".join(row["signals"]) if row["signals"] else "-"
        print(f"{label:<24} {row['fixture_id']:<24} disposition={row['disposition']:<11} risk={row['risk_level']:<8} latency={row['latency_ms']}ms signals={signals}")
    print("=" * 96)
    print("Resultados persistidos y leídos desde rof12.demo_results")


def main() -> None:
    parser = argparse.ArgumentParser(description="ROF12 Baseline vs Protected replay")
    parser.add_argument("--database-url", default=os.getenv("DEMO_DATABASE_URL") or os.getenv("DATABASE_OWNER_URL"))
    parser.add_argument("--run-id", default=str(uuid4()))
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DEMO_DATABASE_URL or DATABASE_OWNER_URL is required")
    started = time.perf_counter()
    fixtures = load_fixtures()
    rows = run_baseline(fixtures) + run_protected(fixtures)
    persisted = persist_and_read(rows, args.database_url, args.run_id)
    if args.json:
        print(json.dumps({"run_id": args.run_id, "total_elapsed_ms": round((time.perf_counter() - started) * 1000, 3), "results": persisted}, default=str, indent=2))
    else:
        print_recording_table(persisted, args.run_id)


if __name__ == "__main__":
    main()
