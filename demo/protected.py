from __future__ import annotations

import time

from app.api.dependencies import AuthContext
from app.perception.file_validator import validate_artifact
from app.perception.ingestion import receive_stream
from app.perception.pdf_inspector import inspect_pdf
from app.perception.risk_analyzer import RiskLevel, analyze_content
from demo.common import DemoFixture


def run(fixtures: tuple[DemoFixture, ...]) -> list[dict]:
    context = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
    results = []
    for fixture in fixtures:
        started = time.perf_counter()
        with fixture.path.open("rb") as stream:
            artifact = receive_stream(context, fixture.path.name, stream)
        validate_artifact(artifact)
        if artifact.extension == ".pdf":
            inspection = inspect_pdf(artifact.content)
            report = analyze_content(inspection.regions, inspection.embedded_text)
            signals = [signal.rule for signal in report.signals]
            risk_level = report.risk_level.value
        else:
            signals = []
            risk_level = RiskLevel.LOW.value
        disposition = "QUARANTINED" if risk_level in {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value} else "REVIEWED"
        results.append(
            {
                "fixture_id": fixture.fixture_id,
                "sha256": fixture.sha256,
                "mode": "PROTECTED",
                "disposition": disposition,
                "risk_level": risk_level,
                "signals": signals,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
    return results
