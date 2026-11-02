import re
from dataclasses import dataclass

from pypdf import PdfReader


@dataclass(frozen=True)
class TextRegion:
    page: int
    text: str
    box: tuple[float, float, float, float]
    font_size: float


@dataclass(frozen=True)
class PdfInspection:
    pages: int
    regions: tuple[TextRegion, ...]
    embedded_text: str
    signals: tuple[str, ...]


def inspect_pdf(content: bytes) -> PdfInspection:
    reader = PdfReader(__import__("io").BytesIO(content), strict=False)
    regions: list[TextRegion] = []
    signals = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text:
            regions.append(TextRegion(page_number, page_text, (0.0, 0.0, float(page.mediabox.width), float(page.mediabox.height)), 12.0))
        resources = page.get("/Resources", {})
        if "/Font" in resources:
            for font_ref in resources["/Font"].values():
                font = font_ref.get_object()
                if "/FontDescriptor" in font and "/FontBBox" in font["/FontDescriptor"]:
                    bbox = font["/FontDescriptor"]["/FontBBox"]
                    if len(bbox) >= 4 and abs(float(bbox[3]) - float(bbox[1])) < 4:
                        signals.append("MICROTEXT_FONT")
        contents = page.get_contents()
        raw = b""
        if contents is not None:
            raw = b"".join(stream.get_data() for stream in (contents if isinstance(contents, list) else [contents]))
        for size in re.findall(rb"(?<![\w.])(\d+(?:\.\d+)?)\s+Tf\b", raw):
            if float(size) < 4:
                signals.append("MICROTEXT")
        if (b"1 1 1" in raw or b"1.0 1.0 1.0" in raw) and b"Tj" in raw:
            signals.append("HIDDEN_WHITE_TEXT")
        if "/Annots" in page:
            signals.append("ANNOTATIONS_PRESENT")
        if "/AA" in page:
            signals.append("HIDDEN_ACTION")
    root = reader.trailer.get("/Root", {})
    if "/OpenAction" in root or "/AA" in root:
        signals.append("OPEN_ACTION")
    raw_document = content
    if any(marker in raw_document for marker in (b"/JavaScript", b"/JS")):
        signals.append("JAVASCRIPT_PRESENT")
    if b"/OCProperties" in raw_document:
        signals.append("OPTIONAL_CONTENT_LAYER")
    return PdfInspection(len(reader.pages), tuple(regions), "\n".join(r.text for r in regions), tuple(sorted(set(signals))))

