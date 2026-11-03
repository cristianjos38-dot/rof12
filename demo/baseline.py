"""Intentionally isolated insecure comparator for the live demonstration.

This module has no imports from ``app`` and uses only an in-memory fictitious
store. It never receives ROF12 credentials, storage paths, or database URLs.
"""
from __future__ import annotations

from demo.common import DemoFixture


def run(fixtures: tuple[DemoFixture, ...]) -> list[dict]:
    return [
        {
            "fixture_id": fixture.fixture_id,
            "sha256": fixture.sha256,
            "mode": "BASELINE",
            "disposition": "EXECUTED",
            "risk_level": "UNASSESSED",
            "signals": [],
            "latency_ms": 0.0,
        }
        for fixture in fixtures
    ]
