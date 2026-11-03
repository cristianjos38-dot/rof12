import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


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
    signals: tuple[RiskSignal, ...]
    evidence_refs: tuple[str, ...]


PATTERNS = (
    ("PROMPT_INJECTION", re.compile(r"ignora|ignore|reembolsa|refund|transfiere|transfer|system:|olvida las reglas|forget the rules", re.IGNORECASE)),
)

INSPECTION_RULES = {
    "HIDDEN_WHITE_TEXT": (RiskLevel.HIGH, "hidden text detected"),
    "MICROTEXT": (RiskLevel.HIGH, "microtext detected"),
    "MICROTEXT_FONT": (RiskLevel.HIGH, "microtext font detected"),
    "ANNOTATIONS_PRESENT": (RiskLevel.MEDIUM, "annotation present"),
    "HIDDEN_ACTION": (RiskLevel.CRITICAL, "hidden action detected"),
    "OPEN_ACTION": (RiskLevel.CRITICAL, "open action detected"),
    "JAVASCRIPT_PRESENT": (RiskLevel.CRITICAL, "embedded javascript detected"),
    "OPTIONAL_CONTENT_LAYER": (RiskLevel.HIGH, "optional content layer detected"),
    "SCANNED_IMAGE_ONLY": (RiskLevel.HIGH, "document has no verifiable embedded text"),
    "MICROTEXT_VISUAL": (RiskLevel.HIGH, "visual microtext signal detected"),
    "LOW_CONTRAST_VISUAL": (RiskLevel.HIGH, "low contrast signal detected"),
}


def analyze_content(
    regions: Iterable,
    embedded_text: str = "",
    discrepancy: bool = False,
    inspection_signals: Iterable[str] = (),
) -> ContentRiskReport:
    signals = []
    for region in regions:
        for rule, pattern in PATTERNS:
            if pattern.search(region.text):
                signals.append(RiskSignal(rule, region.page, region.box, region.text))
    if discrepancy:
        signals.append(RiskSignal("EMBEDDED_VISUAL_DISCREPANCY", 0, (), embedded_text))
    for rule in inspection_signals:
        if rule in INSPECTION_RULES:
            signals.append(RiskSignal(rule, 0, (), INSPECTION_RULES[rule][1]))
    if any(signal.rule == "PROMPT_INJECTION" for signal in signals):
        level = RiskLevel.CRITICAL
    elif any(signal.rule in {"EMBEDDED_VISUAL_DISCREPANCY", "HIDDEN_ACTION", "OPEN_ACTION", "JAVASCRIPT_PRESENT"} for signal in signals):
        level = RiskLevel.HIGH
    elif signals:
        level = max((INSPECTION_RULES.get(signal.rule, (RiskLevel.MEDIUM, ""))[0] for signal in signals), key=lambda item: list(RiskLevel).index(item))
    else:
        level = RiskLevel.LOW
    return ContentRiskReport(level, tuple(signals), tuple(f"{s.rule}:{s.page}" for s in signals))

