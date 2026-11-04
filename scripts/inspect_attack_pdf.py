#!/usr/bin/env python3
"""Basic PDF text/metadata triage; not a complete steganography detector."""
import argparse, json, sys
from pathlib import Path
try:
    from pypdf import PdfReader
except ImportError:
    raise SystemExit("Falta pypdf. Ejecuta: pip install -e '.[pdf]'")
parser = argparse.ArgumentParser()
parser.add_argument("pdf", type=Path)
args = parser.parse_args()
reader = PdfReader(str(args.pdf))
metadata = reader.metadata
meta = {str(k): str(v) for k,v in (metadata or {}).items()}
pages = []
for i, page in enumerate(reader.pages, 1):
    pages.append({"page":i,"text":page.extract_text() or ""})
print(json.dumps({"file":args.pdf.name,"metadata":meta,"pages":pages},indent=2,ensure_ascii=False))
