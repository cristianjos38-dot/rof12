"""Interactive, screen-recording-friendly protected replay."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.common import load_fixtures
from demo.protected import run


VECTORS = {
    "01_legitimate_invoice": "benign invoice",
    "02_scanned_image_only": "image-only document",
    "03_hidden_white_text": "hidden white text",
    "04_prompt_manipulation": "prompt injection",
    "05_tiny_text": "microtext",
    "06_low_contrast": "low contrast",
    "07_ocr_embedded_discrepancy": "OCR/text discrepancy",
}


def paint(text: str, color: str) -> str:
    return f"\033[{color}m{text}\033[0m"


def main() -> None:
    parser = argparse.ArgumentParser(description="ROF12 video demonstration runner")
    parser.add_argument("--interactive", action="store_true", help="press Enter before each fixture")
    parser.add_argument("--pause", type=float, default=1.5, help="seconds between fixtures")
    args = parser.parse_args()
    for result in run(load_fixtures()):
        if args.interactive:
            input("\nPress Enter for the next case... ")
        blocked = result["decision"] in {"DENY", "QUARANTINE"}
        label = paint("BLOCKED", "31") if blocked else paint("ALLOW", "32")
        trace = result.get("meta_trace", {})
        print("\n" + paint("═" * 72, "36"))
        print(paint(f"{result['fixture_id']} · {VECTORS[result['fixture_id']]}", "1;36"))
        print(f"Meta Spark: {trace.get('spark_model')} [{trace.get('spark_source')}] risk={trace.get('spark_risk')}")
        print(f"Meta SAM:   {trace.get('sam_model')} [{trace.get('sam_source')}] boxes={trace.get('evidence_boxes') or '-'} masks={trace.get('evidence_masks') or '-'}")
        print(f"Meta Wonder: {trace.get('wonder_model')} [{trace.get('wonder_source')}] proposal_present={trace.get('wonder_proposal_present')} gate_required={trace.get('wonder_gate_required')}")
        print(f"Gate decision: {label} ({result['decision']})")
        print(f"SHA-256: {result['sha256']}")
        print("Supabase hash confirmation: checked by persisted replay when DATABASE_OWNER_URL is configured")
        time.sleep(args.pause)


if __name__ == "__main__":
    main()
