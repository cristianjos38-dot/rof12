import re
from pathlib import Path


def test_every_threat_id_has_adversarial_test():
    threat_model = Path("docs/THREAT_MODEL.md").read_text(encoding="utf-8")
    threat_ids = sorted(set(re.findall(r"T-\d{2}", threat_model)))
    adversarial_text = "\n".join(path.read_text(encoding="utf-8") for path in Path("tests/adversarial").glob("test_*.py"))
    missing = [threat_id for threat_id in threat_ids if threat_id not in adversarial_text]
    assert not missing, f"missing adversarial coverage: {missing}"

