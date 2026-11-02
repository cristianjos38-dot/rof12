from io import BytesIO

import pypdfium2 as pdfium

from app.perception.ocr_engine import OcrEngine


def render_pdf_pages(content: bytes, dpi: int = 160) -> list[bytes]:
    if dpi < 150 or dpi > 200:
        raise ValueError("render DPI must be between 150 and 200")
    document = pdfium.PdfDocument(content)
    images = []
    scale = dpi / 72.0
    for index in range(len(document)):
        bitmap = document[index].render(scale=scale)  # type: ignore[arg-type]
        image = bitmap.to_pil()
        output = BytesIO()
        image.save(output, format="PNG", optimize=False)
        images.append(output.getvalue())
    return images


def analyze_visual_pdf(content: bytes, ocr_engine: OcrEngine, dpi: int = 160) -> tuple:
    images = render_pdf_pages(content, dpi=dpi)
    return tuple(ocr_engine.recognize(images))


def compare_texts(embedded_text: str, visual_regions: tuple) -> tuple:
    visual_text = " ".join(region.text for region in visual_regions)
    embedded_amounts = set(__import__("re").findall(r"Q\s*\d+[\d,]*\.\d{2}", embedded_text, flags=__import__("re").I))
    visual_amounts = set(__import__("re").findall(r"Q\s*\d+[\d,]*\.\d{2}", visual_text, flags=__import__("re").I))
    return embedded_amounts, visual_amounts, embedded_amounts != visual_amounts

