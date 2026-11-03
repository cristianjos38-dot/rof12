from demo.common import load_fixtures
from demo.protected import run


def test_protected_demo_allows_only_benign_fixture_and_blocks_adversarial_corpus():
    results = run(load_fixtures())
    assert len(results) == 7
    assert [row["decision"] for row in results] == ["ALLOW", "QUARANTINE", "QUARANTINE", "QUARANTINE", "QUARANTINE", "QUARANTINE", "QUARANTINE"]
    assert results[0]["fixture_id"] == "01_legitimate_invoice"
    assert all(row["decision"] == "QUARANTINE" for row in results[1:])
    assert all(row["signals"] for row in results[1:])
