from pathlib import Path
from types import SimpleNamespace

from app.api.dependencies import AuthContext
from app.perception.pdf_inspector import inspect_pdf
from app.perception.risk_analyzer import analyze_content
from app.security.policy_engine import GateDecision, evaluate


def test_prompt_injection_is_signal_not_authority():
    # T-04
    content = (Path("tests/fixtures/adversarial/04_prompt_manipulation.pdf")).read_bytes()
    inspection = inspect_pdf(content)
    report = analyze_content(inspection.regions, inspection.embedded_text)
    result = evaluate(AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001"), SimpleNamespace(tool_name="refund_service"), SimpleNamespace(valid=True, reasons=()), SimpleNamespace(is_tainted=True), report, SimpleNamespace(checks={"V2": True, "V4": True, "V5": True}), SimpleNamespace(active=False))
    assert report.signals
    assert result.decision in {GateDecision.QUARANTINE, GateDecision.DENY}

