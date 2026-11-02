from pathlib import Path

from app.perception.ocr_engine import FixtureOcrEngine, OcrRegion
from app.perception.pdf_inspector import inspect_pdf
from app.perception.risk_analyzer import RiskLevel, analyze_content
from app.perception.visual_analysis import analyze_visual_pdf, compare_texts


def test_visual_and_embedded_amounts_cannot_disagree_silently():
    # T-08
    content = (Path("tests/fixtures/adversarial/07_ocr_embedded_discrepancy.pdf")).read_bytes()
    inspection = inspect_pdf(content)
    visual = analyze_visual_pdf(content, FixtureOcrEngine((OcrRegion(1, "Q150.00", (0, 0, 1, 1)),)))
    embedded, visual_amounts, mismatch = compare_texts(inspection.embedded_text, visual)
    report = analyze_content(inspection.regions, inspection.embedded_text, mismatch)
    assert "Q900.00" in embedded and "Q150.00" in visual_amounts
    assert report.risk_level is RiskLevel.HIGH

