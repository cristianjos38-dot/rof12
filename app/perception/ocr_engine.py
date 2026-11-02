from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OcrRegion:
    page: int
    text: str
    box: tuple


class OcrEngine(Protocol):
    def recognize(self, page_images: Sequence[bytes]) -> Sequence[OcrRegion]: ...


class PaddleOcrEngine:
    """Optional adapter; deterministic tests inject a local fallback engine."""

    def __init__(self):
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except ImportError:
            self._engine = None
        else:
            self._engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    def recognize(self, page_images: Sequence[bytes]) -> Sequence[OcrRegion]:
        if self._engine is None:
            return ()
        from io import BytesIO

        from PIL import Image

        regions = []
        for page, raw in enumerate(page_images, start=1):
            image = Image.open(BytesIO(raw))
            result = self._engine.ocr(__import__("numpy").array(image), cls=True)
            for line in result[0] or []:
                regions.append(OcrRegion(page, str(line[1][0]), tuple(line[0][0] + line[0][2])))
        return tuple(regions)


class FixtureOcrEngine:
    """Offline fixture adapter used to test discrepancy policy without an LLM or network."""

    def __init__(self, regions: Sequence[OcrRegion]):
        self._regions = tuple(regions)

    def recognize(self, page_images: Sequence[bytes]) -> Sequence[OcrRegion]:
        return self._regions

