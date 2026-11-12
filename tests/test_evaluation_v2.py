from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from rof12.corpus_v2 import cases, evaluate_live_case


pytestmark = pytest.mark.skipif(
    not (os.getenv("DATABASE_OWNER_URL") and os.getenv("ROF12_EXECUTOR_DB_URL")),
    reason="DATABASE_OWNER_URL and ROF12_EXECUTOR_DB_URL are required for live corpus evaluation",
)


def _run_live(case: dict, document_text: str = "synthetic clean document"):
    owner = create_engine(os.environ["DATABASE_OWNER_URL"])
    executor = create_engine(os.environ["ROF12_EXECUTOR_DB_URL"])
    with owner.begin() as connection:
        # Seeding is isolated to the owner connection; decisions use the executor role.
        from rof12.corpus_v2 import seed_case
        seed_case(connection, case, document_text)
    with executor.begin() as connection:
        return evaluate_live_case(connection, case, document_text, seed=False)


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
