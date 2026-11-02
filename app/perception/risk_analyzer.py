from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable, Tuple


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class RiskSignal:
    rule: str
    page: int
    box: tuple
    text: str


@dataclass(frozen=True)
class ContentRiskReport:
    risk_level: RiskLevel
    signals: Tuple[RiskSignal, ...]
    evidence_refs: Tuple[str, ...]


PATTERNS = (
    ("PROMPT_INJECTION", re.compile(r"ignora|ignore|reembolsa|refund|transfiere|transfer|system:|olvida las reglas|forget the rules", re.I)),
)


def analyze_content(regions: Iterable, embedded_text: str = "", discrepancy: bool = False) -> ContentRiskReport:
    signals = []
    for region in regions:
        for rule, pattern in PATTERNS:
            if pattern.search(region.text):
                signals.append(RiskSignal(rule, region.page, region.box, region.text))
    if discrepancy:
        signals.append(RiskSignal("EMBEDDED_VISUAL_DISCREPANCY", 0, (), embedded_text))
    if any(signal.rule == "PROMPT_INJECTION" for signal in signals):
        level = RiskLevel.CRITICAL
    elif any(signal.rule == "EMBEDDED_VISUAL_DISCREPANCY" for signal in signals):
        level = RiskLevel.HIGH
    elif signals:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW
    return ContentRiskReport(level, tuple(signals), tuple("%s:%s" % (s.rule, s.page) for s in signals))

