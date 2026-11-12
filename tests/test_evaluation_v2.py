import json
from pathlib import Path

from rof12.corpus_v2 import cases, evaluate_case


def test_v2_corpus_has_documented_terminal_verdicts():
    entries = cases()
    assert len(entries) == 18
    for case in entries:
        result = evaluate_case(case)
        assert result.decision.value == case["expected"], case["id"]
        assert case["reason"] in result.reasons, case["id"]


def test_legitimate_corpus_has_zero_false_positives():
    fixtures = json.loads(Path("tests/fixtures/legitimate_corpus_v2.json").read_text())
    assert len(fixtures) == 20
    assert all(item["expected"] == "ALLOW" for item in fixtures)
