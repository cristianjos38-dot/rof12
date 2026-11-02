from pathlib import Path

from app.perception.file_validator import validate_artifact
from app.perception.ingestion import receive_stream
from app.perception.ocr_engine import FixtureOcrEngine, OcrRegion
from app.perception.pdf_inspector import inspect_pdf
from app.perception.risk_analyzer import RiskLevel, analyze_content
from app.perception.visual_analysis import analyze_visual_pdf, compare_texts

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "adversarial"


def test_seven_adversarial_fixtures_are_received_and_validated():
    from io import BytesIO

    from app.api.dependencies import AuthContext

    context = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
    for path in sorted(FIXTURES.iterdir()):
        artifact = receive_stream(context, path.name, BytesIO(path.read_bytes()))
        assert artifact.state.value == "RECEIVED"
        assert validate_artifact(artifact).valid is True


def test_prompt_injection_and_hidden_text_emit_signals():
    prompt = inspect_pdf((FIXTURES / "04_prompt_manipulation.pdf").read_bytes())
    report = analyze_content(prompt.regions, prompt.embedded_text)
    assert report.risk_level is RiskLevel.CRITICAL
    assert any(signal.rule == "PROMPT_INJECTION" for signal in report.signals)
    hidden = inspect_pdf((FIXTURES / "03_hidden_white_text.pdf").read_bytes())
    assert "HIDDEN_WHITE_TEXT" in hidden.signals


def test_visual_ocr_discrepancy_is_signal_without_authority():
    content = (FIXTURES / "07_ocr_embedded_discrepancy.pdf").read_bytes()
    inspection = inspect_pdf(content)
    visual = analyze_visual_pdf(content, FixtureOcrEngine((OcrRegion(1, "Imagen OCR: Q150.00", (0, 0, 1, 1)),)))
    embedded, visual_amounts, discrepancy = compare_texts(inspection.embedded_text, visual)
    assert "Q900.00" in embedded
    assert "Q150.00" in visual_amounts
    assert discrepancy is True
    report = analyze_content(inspection.regions, inspection.embedded_text, discrepancy)
    assert report.risk_level is RiskLevel.HIGH
    assert all(signal.rule != "ALLOW" for signal in report.signals)

