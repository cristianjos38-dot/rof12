"""Provider interfaces. Mock adapters are test doubles, not real model inference."""
from dataclasses import dataclass

@dataclass
class SparkResult:
    injection_detected: bool
    label: str

class MuseSparkAdapter:
    def analyze(self, visible_text: str, hidden_text: str) -> SparkResult:
        # TODO: replace with authorized Muse Spark 1.3 integration.
        suspicious = any(term in hidden_text.lower() for term in
                         ("instruction:", "ignore audit", "transferir", "delete logs", "borrar logs"))
        return SparkResult(suspicious, "PROMPT_INJECTION_DETECTED" if suspicious else "CLEAN")

class SAMAdapter:
    def segment(self, document_id: str, bounding_box=None) -> dict:
        # TODO: replace with SAM 3.1 segmentation over rendered page/image.
        return {"has_boxes": bool(bounding_box), "has_masks": bool(bounding_box),
                "provider": "mock", "note": "No real segmentation was performed."}
