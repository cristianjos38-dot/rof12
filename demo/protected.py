from __future__ import annotations

import time
from io import BytesIO

from PIL import Image, ImageStat

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
            inspection_signals = list(inspection.signals)
            if not inspection.embedded_text.strip():
                inspection_signals.append("SCANNED_IMAGE_ONLY")
            report = analyze_content(
                inspection.regions,
                inspection.embedded_text,
                inspection_signals=inspection_signals,
            )
            signals = [signal.rule for signal in report.signals]
            risk_level = report.risk_level.value
        else:
            image = Image.open(BytesIO(artifact.content)).convert("L")
            stats = ImageStat.Stat(image)
            signals = []
            if stats.extrema[0][0] < 64:
                signals.append("MICROTEXT_VISUAL")
            if stats.extrema[0][0] > 200 and stats.stddev[0] < 8:
                signals.append("LOW_CONTRAST_VISUAL")
            report = analyze_content((), inspection_signals=signals)
            risk_level = report.risk_level.value
        blocked = bool(signals) or risk_level in {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}
        decision = "QUARANTINE" if blocked else "ALLOW"
        disposition = "QUARANTINED" if blocked else "ALLOWED"
        results.append(
            {
                "fixture_id": fixture.fixture_id,
                "sha256": fixture.sha256,
                "mode": "PROTECTED",
                "disposition": disposition,
                "decision": decision,
                "risk_level": risk_level,
                "signals": signals,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        )
    return results
