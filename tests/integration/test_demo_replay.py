from pathlib import Path

from demo.baseline import run as run_baseline
from demo.common import load_fixtures


def test_demo_uses_exactly_the_same_seven_fixtures_for_baseline():
    fixtures = load_fixtures()
    rows = run_baseline(fixtures)
    assert len(fixtures) == 7
    assert [row["sha256"] for row in rows] == [fixture.sha256 for fixture in fixtures]
    assert {row["mode"] for row in rows} == {"BASELINE"}


def test_baseline_has_no_protected_runtime_imports():
    source = Path("demo/baseline.py").read_text(encoding="utf-8")
    assert "from app" not in source
    assert "DATABASE_URL" not in source
