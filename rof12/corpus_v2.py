"""PostgreSQL-backed evaluator for the versioned defensive corpus."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import text

from app.domain.contracts import ToolRequest
from app.provenance import TaintedValue
from app.security.capability_manager import CapabilityRecord, CapabilityStatus, hash_capability, validate
from app.security.kill_switch import KillSwitch
from app.security.security_gate import SecurityGate
from app.verification.verityflow import evaluate


def cases() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "attacks" / "v2_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def _case_shape(case: dict) -> dict:
    """Map a vector to concrete fixture data; never to an expected verdict."""
    vector = case["vector"]
    invalid = {"replayed_agent_message", "expired_capability", "forged_approval", "audit_chain_fork"}
    return {
        "tenant_id": "tenant_002" if vector == "tenant_substitution" else "tenant_001",
        "status": "CONSUMED" if vector == "replayed_agent_message" else "ACTIVE",
        "expired": vector == "expired_capability",
        "max_amount": Decimal("1.00") if vector in {"amount_precision_overflow", "toctou_resource_change"} else Decimal("200.00"),
        "amount": Decimal("200.01") if vector in {"negative_amount", "amount_precision_overflow"} else Decimal("10.00"),
        "balance": Decimal("0.00") if vector == "toctou_resource_change" else Decimal("250.00"),
        "tainted": vector in {"multi_step_injection", "tool_output_poisoning", "unicode_homoglyph", "oversized_document", "malformed_pdf", "contradictory_pdf_layers", "hidden_macro_instruction", "ocr_amount_mismatch"},
        "duplicate": vector == "double_spend_race",
        "tool_name": "unknown_tool" if vector == "unknown_tool_alias" else "refund_service",
        "operation_id": f"corpus-v2-{case['id']}",
        "invalid_capability": vector in invalid,
    }


def seed_case(connection, case: dict, document_text: str = "synthetic clean document") -> dict:
    """Seed one isolated order, capability and document for a live evaluation."""
    shape = _case_shape(case)
    vector_id = case["id"].lower().replace("-", "_")
    tenant_id = shape["tenant_id"]
    order_id = f"corpus_{vector_id}"
    capability_id = f"cap_{vector_id}"
    token = f"corpus-token-{vector_id}"
    now = datetime.now(UTC)
    expires = now - timedelta(minutes=1) if shape["expired"] else now + timedelta(minutes=10)
    connection.execute(text("""
        INSERT INTO rof12.orders (tenant_id, order_id, owner_user_id, status, refundable_balance)
        VALUES (:tenant_id, :order_id, :owner_user_id, 'PAID', :balance)
        ON CONFLICT (tenant_id, order_id) DO UPDATE SET refundable_balance = EXCLUDED.refundable_balance
    """), {"tenant_id": tenant_id, "order_id": order_id, "owner_user_id": "user_001" if tenant_id == "tenant_001" else "user_002", "balance": shape["balance"]})
    connection.execute(text("""
        INSERT INTO rof12.capabilities
          (capability_id, tenant_id, subject_user_id, token_hash, scope, max_amount, status, expires_at)
        VALUES (:id, 'tenant_001', 'user_001', :token_hash, 'refund', :max_amount, :status, :expires)
        ON CONFLICT (capability_id) DO UPDATE SET status = EXCLUDED.status, expires_at = EXCLUDED.expires_at, max_amount = EXCLUDED.max_amount
    """), {"id": capability_id, "token_hash": hash_capability(token), "max_amount": shape["max_amount"], "status": "CONSUMED" if shape["invalid_capability"] and not shape["expired"] else "ACTIVE", "expires": expires})
    provenance_id = f"prov_{vector_id}"
    digest = hashlib.sha256(document_text.encode()).hexdigest()
    connection.execute(text("""
            INSERT INTO rof12.provenance_records
              (tenant_id, provenance_id, source_type, source_uri, fragment_hash, contamination_status)
            VALUES ('tenant_001', :id, 'fixture', :uri, :digest, :status)
            ON CONFLICT (tenant_id, provenance_id) DO UPDATE SET contamination_status = EXCLUDED.contamination_status
        """), {"id": provenance_id, "uri": f"fixture://{case['id']}", "digest": digest, "status": "TAINTED" if shape["tainted"] else "RECONCILED"})
    connection.execute(text("""
            INSERT INTO rof12.documents
              (tenant_id, document_id, original_filename, media_type, byte_size, content_sha256, storage_key, provenance_id, created_by)
            VALUES ('tenant_001', :id, :filename, 'text/plain', :size, :digest, :storage, :provenance, 'user_001')
            ON CONFLICT (tenant_id, document_id) DO UPDATE SET content_sha256 = EXCLUDED.content_sha256
        """), {"id": vector_id, "filename": f"{case['id']}.txt", "size": max(1, len(document_text)), "digest": digest, "storage": f"fixture/{vector_id}", "provenance": provenance_id})
    connection.execute(text("""
        INSERT INTO rof12.document_fragments
          (tenant_id, document_id, fragment_id, ordinal, content_sha256, text_content, is_tainted)
        VALUES ('tenant_001', :document_id, 'fragment-1', 0, :digest, :text_content, :is_tainted)
        ON CONFLICT (tenant_id, document_id, fragment_id) DO UPDATE SET text_content = EXCLUDED.text_content, is_tainted = EXCLUDED.is_tainted
    """), {"document_id": vector_id, "digest": digest, "text_content": document_text, "is_tainted": shape["tainted"]})
    if shape["duplicate"]:
        connection.execute(text("""
            INSERT INTO rof12.refunds (refund_id, tenant_id, order_id, operation_id, amount, status)
            VALUES (:refund_id, 'tenant_001', :order_id, :operation_id, 10.00, 'EXECUTED')
            ON CONFLICT (tenant_id, operation_id) DO NOTHING
        """), {"refund_id": f"seed-{vector_id}", "order_id": order_id, "operation_id": shape["operation_id"]})
    return {**shape, "order_id": order_id, "capability_id": capability_id, "token": token}


def evaluate_live_case(connection, case: dict, document_text: str = "synthetic clean document", *, seed: bool = True):
    shape = seed_case(connection, case, document_text) if seed else _case_shape(case) | {
        "order_id": f"corpus_{case['id'].lower().replace('-', '_')}",
        "capability_id": f"cap_{case['id'].lower().replace('-', '_')}",
        "token": f"corpus-token-{case['id'].lower().replace('-', '_')}",
    }
    context = SimpleNamespace(user_id="user_001", tenant_id="tenant_001", membership_status="ACTIVE", role="operator")
    connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": "tenant_001"})
    capability_row = connection.execute(text("""
        SELECT capability_id, tenant_id, subject_user_id, token_hash, status, expires_at, max_amount
          FROM rof12.capabilities WHERE capability_id = :id
    """), {"id": shape["capability_id"]}).mappings().first()
    capability = CapabilityRecord(
        capability_row["capability_id"], capability_row["tenant_id"], capability_row["subject_user_id"], capability_row["token_hash"],
        CapabilityStatus(capability_row["status"]), capability_row["expires_at"], Decimal(str(capability_row["max_amount"])),
    )
    request = ToolRequest(order_id=shape["order_id"], amount=shape["amount"], reason="corpus fixture", operation_id=shape["operation_id"])
    verity = evaluate(connection, request, context, capability, datetime.now(UTC))
    document = connection.execute(text("""
        SELECT text_content, is_tainted FROM rof12.document_fragments
         WHERE tenant_id = 'tenant_001' AND document_id = :document_id AND fragment_id = 'fragment-1'
    """), {"document_id": case["id"].lower().replace("-", "_")}).mappings().first()
    document_value = document["text_content"] if document else document_text
    provenance = TaintedValue.external(document_value, f"fixture://{case['id']}") if document and document["is_tainted"] else TaintedValue.trusted(document_value)
    return SecurityGate().evaluate(
        context, SimpleNamespace(tool_name=shape["tool_name"]), validate(capability, request, context, datetime.now(UTC)),
        provenance, SimpleNamespace(risk_level="HIGH" if shape["tainted"] else "LOW"), verity, KillSwitch().read(connection),
    )
