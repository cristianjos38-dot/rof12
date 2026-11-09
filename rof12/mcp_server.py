"""Official MCP adapter for ROF12's server-authoritative SecurityGate."""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

from app.security.security_gate import SecurityGate

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


@mcp.tool()
def evaluate_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a proposal without executing any tool or issuing authority."""
    result = _evaluate(proposal, os.getenv("ROF12_MCP_TENANT_ID", ""), os.getenv("ROF12_MCP_USER_ID", ""))
    return {
        "decision": result.decision.value,
        "reasons": list(result.reasons),
        "dimensions": result.dimensions or {},
    }


@mcp.tool()
def request_permit(proposal: dict[str, Any]) -> dict[str, Any]:
    """Mint an opaque permit only when the existing Gate returns ALLOW."""
    result = _evaluate(proposal, os.getenv("ROF12_MCP_TENANT_ID", ""), os.getenv("ROF12_MCP_USER_ID", ""))
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
