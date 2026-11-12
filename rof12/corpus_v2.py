"""Deterministic evaluator for the versioned defensive corpus."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.security.security_gate import SecurityGate


def cases() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "attacks" / "v2_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def evaluate_case(case: dict):
    vector = case["vector"]
    context = SimpleNamespace(user_id="user_001", tenant_id="tenant_001", membership_status="ACTIVE")
    request = SimpleNamespace(tool_name="drop_database" if vector == "unknown_tool_alias" else "refund_service")
    invalid_authority = {"replayed_agent_message", "expired_capability", "forged_approval", "audit_chain_fork"}
    capability = SimpleNamespace(valid=vector not in invalid_authority, reasons=())
    tainted_vectors = {
        "multi_step_injection", "tool_output_poisoning", "unicode_homoglyph",
        "oversized_document", "malformed_pdf", "contradictory_pdf_layers",
        "hidden_macro_instruction", "ocr_amount_mismatch",
    }
    provenance = SimpleNamespace(is_tainted=vector in tainted_vectors)
    risk = SimpleNamespace(risk_level="HIGH" if provenance.is_tainted else "LOW")
    verity = SimpleNamespace(
        checks={
            "V2": vector != "tenant_substitution",
            "V4": vector not in {"negative_amount", "amount_precision_overflow"},
            "V5": vector not in {"toctou_resource_change", "double_spend_race"},
        },
        approval_required=False,
    )
    return SecurityGate().evaluate(context, request, capability, provenance, risk, verity, SimpleNamespace(active=False))
