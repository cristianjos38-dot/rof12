from pathlib import Path

from app.perception.pdf_inspector import inspect_pdf


def test_white_text_is_detected():
    # T-08
    report = inspect_pdf((Path("tests/fixtures/adversarial/03_hidden_white_text.pdf")).read_bytes())
    assert "HIDDEN_WHITE_TEXT" in report.signals

