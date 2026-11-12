from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from rof12.corpus_v2 import cases, evaluate_live_case


pytestmark = pytest.mark.skipif(
    not (os.getenv("DATABASE_OWNER_URL") and os.getenv("ROF12_EXECUTOR_DB_URL")),
    reason="DATABASE_OWNER_URL and ROF12_EXECUTOR_DB_URL are required for live corpus evaluation",
)


def _run_live(case: dict, document_text: str = "synthetic clean document"):
    owner = create_engine(os.environ["DATABASE_OWNER_URL"])
    executor = create_engine(os.environ["ROF12_EXECUTOR_DB_URL"])
    from rof12.corpus_v2 import seed_case
    try:
        with owner.begin() as connection:
            # Seeding is isolated to the owner connection; decisions use the executor role.
            seed_case(connection, case, document_text)
        with executor.begin() as connection:
            return evaluate_live_case(connection, case, document_text, seed=False)
    finally:
        vector_id = case["id"].lower().replace("-", "_")
        with owner.begin() as connection:
            connection.execute(text("DELETE FROM rof12.refunds WHERE operation_id = :operation_id"), {"operation_id": f"corpus-v2-{case['id']}"})
            connection.execute(text("DELETE FROM rof12.document_fragments WHERE document_id = :document_id"), {"document_id": vector_id})
            connection.execute(text("DELETE FROM rof12.documents WHERE document_id = :document_id"), {"document_id": vector_id})
            connection.execute(text("DELETE FROM rof12.provenance_records WHERE provenance_id = :provenance_id"), {"provenance_id": f"prov_{vector_id}"})
            connection.execute(text("DELETE FROM rof12.capabilities WHERE capability_id = :capability_id"), {"capability_id": f"cap_{vector_id}"})
            connection.execute(text("DELETE FROM rof12.orders WHERE order_id = :order_id"), {"order_id": f"corpus_{vector_id}"})


def test_v2_corpus_runs_real_postgres_pipeline():
    entries = cases()
    assert len(entries) == 18
    for case in entries:
        result = _run_live(case, f"synthetic document for {case['id']}")
        assert result.decision.value == case["expected"], case["id"]
        assert case["reason"] in result.reasons, case["id"]


def test_legitimate_corpus_has_zero_false_positives_from_each_fixture():
    fixtures = json.loads(Path("tests/fixtures/legitimate_corpus_v2.json").read_text())
    assert len(fixtures) == 20
    for fixture in fixtures:
        case = {"id": fixture["id"], "vector": "legitimate_document"}
        result = _run_live(case, fixture["document"])
        assert result.decision.value == fixture["expected"], fixture["id"]
