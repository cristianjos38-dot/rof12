from __future__ import annotations

import argparse
import json
import os
from uuid import uuid4

from sqlalchemy import create_engine, text

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
    risk_level TEXT NOT NULL,
    signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, fixture_id, mode)
)
"""


def persist_and_read(rows: list[dict], database_url: str, run_id: str) -> list[dict]:
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text(CREATE_RESULTS))
        for row in rows:
            connection.execute(
                text("""
                    INSERT INTO rof12.demo_results
                        (run_id, fixture_id, sha256, mode, disposition, risk_level, signals)
                    VALUES (:run_id, :fixture_id, :sha256, :mode, :disposition, :risk_level, CAST(:signals AS jsonb))
                """),
                {**row, "run_id": run_id, "signals": json.dumps(row["signals"])},
            )
        result = connection.execute(
            text("""
                SELECT fixture_id, sha256, mode, disposition, risk_level, signals
                FROM rof12.demo_results
                WHERE run_id = :run_id
                ORDER BY fixture_id, mode
            """),
            {"run_id": run_id},
        ).mappings()
        return [dict(row) for row in result]


def main() -> None:
    parser = argparse.ArgumentParser(description="ROF12 Baseline vs Protected replay")
    parser.add_argument("--database-url", default=os.getenv("DEMO_DATABASE_URL") or os.getenv("DATABASE_OWNER_URL"))
    parser.add_argument("--run-id", default=str(uuid4()))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DEMO_DATABASE_URL or DATABASE_OWNER_URL is required")
    fixtures = load_fixtures()
    rows = run_baseline(fixtures) + run_protected(fixtures)
    print(json.dumps(persist_and_read(rows, args.database_url, args.run_id), default=str, indent=2))


if __name__ == "__main__":
    main()
