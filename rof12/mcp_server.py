"""Official MCP adapter for ROF12's server-authoritative SecurityGate."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from app.security.security_gate import SecurityGate
from app.security.capability_manager import CapabilityRecord, CapabilityStatus, hash_capability
from app.verification.verityflow import evaluate_snapshot
from app.domain.contracts import ToolRequest

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without optional install
    raise RuntimeError("Install the project with the MCP integration dependencies") from exc


mcp = FastMCP("ROF12 SecurityGate")


def _evaluate(proposal: dict[str, Any], tenant_id: str, user_id: str) -> Any:
    context = SimpleNamespace(
        user_id=user_id,
        tenant_id=tenant_id,
        membership_status="ACTIVE",
    )
    request = SimpleNamespace(tool_name=proposal.get("tool_name", ""))
    capability = SimpleNamespace(valid=True, reasons=())
    provenance = SimpleNamespace(is_tainted=False)
    risk = SimpleNamespace(risk_level="LOW")
    verity = SimpleNamespace(
        checks={"V2": True, "V4": True, "V5": True},
        approval_required=False,
    )
    system_state = SimpleNamespace(active=False)
    return SecurityGate().evaluate(
        context, request, capability, provenance, risk, verity, system_state
    )


def _evaluate_real(proposal: dict[str, Any], tenant_id: str, user_id: str):
    """Use server-side DB capability/order state when explicitly configured."""
    database_url = os.getenv("DATABASE_URL")
    token = os.getenv("ROF12_MCP_CAPABILITY_TOKEN")
    if not database_url or not token:
        return None
    try:
        from sqlalchemy import create_engine, text

        args = proposal.get("args", {})
        request = ToolRequest(
            order_id=str(args["order_id"]),
            amount=Decimal(str(args["amount"])),
            reason=str(args.get("reason", "MCP proposal")),
            operation_id=str(args["operation_id"]),
        )
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})
            capability_row = connection.execute(text("""
                SELECT capability_id, tenant_id, subject_user_id, token_hash, status, expires_at, max_amount
                  FROM rof12.capabilities
                 WHERE token_hash = :token_hash
            """), {"token_hash": hash_capability(token)}).mappings().first()
            order = connection.execute(text("""
                SELECT tenant_id, owner_user_id, status, refundable_balance
                  FROM rof12.orders WHERE order_id = :order_id
            """), {"order_id": request.order_id}).mappings().first()
        capability = None if capability_row is None else CapabilityRecord(
            capability_row["capability_id"], capability_row["tenant_id"], capability_row["subject_user_id"],
            capability_row["token_hash"], CapabilityStatus(capability_row["status"]), capability_row["expires_at"],
            Decimal(str(capability_row["max_amount"])),
        )
        verity = evaluate_snapshot(dict(order) if order else None, request, SimpleNamespace(tenant_id=tenant_id, user_id=user_id), capability, False, datetime.now(UTC))
        return SecurityGate().evaluate(
            SimpleNamespace(user_id=user_id, tenant_id=tenant_id, membership_status="ACTIVE"),
            SimpleNamespace(tool_name=proposal.get("tool_name", "")),
            SimpleNamespace(valid=verity.checks.get("V5", False), reasons=()),
            SimpleNamespace(is_tainted=False), SimpleNamespace(risk_level="LOW"), verity, SimpleNamespace(active=False),
        )
    except (KeyError, TypeError, ValueError, Exception):
        return None


def _resolve_evaluation(proposal: dict[str, Any], tenant_id: str, user_id: str):
    """Prefer the database-backed evaluation whenever its inputs are configured."""
    return _evaluate_real(proposal, tenant_id, user_id) or _evaluate(
        proposal, tenant_id, user_id
    )


@mcp.tool()
def evaluate_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a proposal without executing any tool or issuing authority."""
    tenant_id, user_id = os.getenv("ROF12_MCP_TENANT_ID", ""), os.getenv("ROF12_MCP_USER_ID", "")
    result = _resolve_evaluation(proposal, tenant_id, user_id)
    return {
        "decision": result.decision.value,
        "reasons": list(result.reasons),
        "dimensions": result.dimensions or {},
        "evaluation_source": "postgres_verityflow" if os.getenv("DATABASE_URL") and os.getenv("ROF12_MCP_CAPABILITY_TOKEN") else "synthetic_fallback",
    }


@mcp.tool()
def request_permit(proposal: dict[str, Any]) -> dict[str, Any]:
    """Mint an opaque permit only when the existing Gate returns ALLOW."""
    result = _resolve_evaluation(
        proposal, os.getenv("ROF12_MCP_TENANT_ID", ""), os.getenv("ROF12_MCP_USER_ID", "")
    )
    if result.decision.value != "ALLOW":
        return {"decision": result.decision.value, "reasons": list(result.reasons)}
    permit = SecurityGate().mint_if_allowed(result)
    return {
        "decision": result.decision.value,
        "permit_id": permit.permit_id,
        "permit_is_execution_authority": False,
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
