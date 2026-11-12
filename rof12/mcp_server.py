"""Official MCP adapter for ROF12's server-authoritative SecurityGate."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.domain.contracts import ToolRequest
from app.security.capability_manager import (
    CapabilityRecord,
    CapabilityStatus,
    hash_capability,
    validate as validate_capability,
)
from app.security.kill_switch import KillSwitch
from app.security.security_gate import SecurityGate
from app.services.refund_workflow import RefundWorkflow
from app.verification.verityflow import evaluate_snapshot

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without optional install
    raise RuntimeError("Install the project with the MCP integration dependencies") from exc


mcp = FastMCP("ROF12 SecurityGate")


class MCPError(RuntimeError):
    """A fail-closed MCP rejection with a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _configured() -> tuple[str, str, str, str]:
    database_url = os.getenv("DATABASE_URL", "")
    token = os.getenv("ROF12_MCP_CAPABILITY_TOKEN", "")
    tenant_id = os.getenv("ROF12_MCP_TENANT_ID", "")
    user_id = os.getenv("ROF12_MCP_USER_ID", "")
    if not all((database_url, token, tenant_id, user_id)):
        raise MCPError(
            "MCP_NOT_CONFIGURED",
            "DATABASE_URL, capability token, tenant id, and user id are required",
        )
    return database_url, token, tenant_id, user_id


def _request_from_proposal(proposal: dict[str, Any]) -> ToolRequest:
    if not isinstance(proposal, dict):
        raise MCPError("MALFORMED_PROPOSAL", "proposal must be an object")
    args = proposal.get("args")
    if not isinstance(args, dict):
        raise MCPError("MALFORMED_PROPOSAL", "proposal.args must be an object")
    try:
        amount = Decimal(str(args["amount"]))
        return ToolRequest(
            order_id=str(args["order_id"]),
            amount=amount,
            reason=str(args.get("reason", "MCP proposal")),
            operation_id=str(args["operation_id"]),
        )
    except (KeyError, InvalidOperation, TypeError, ValueError) as exc:
        raise MCPError("MALFORMED_PROPOSAL", "order_id, amount, and operation_id are required") from exc


def _evaluate_real(proposal: dict[str, Any]) -> tuple[Any, str]:
    database_url, token, tenant_id, user_id = _configured()
    request = _request_from_proposal(proposal)
    context = SimpleNamespace(
        user_id=user_id,
        tenant_id=tenant_id,
        membership_status="ACTIVE",
        role="operator",
    )
    now = datetime.now(UTC)
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": tenant_id},
            )
            capability_row = connection.execute(
                text("""
                    SELECT capability_id, tenant_id, subject_user_id, token_hash,
                           status, expires_at, max_amount
                      FROM rof12.capabilities
                     WHERE token_hash = :token_hash
                """),
                {"token_hash": hash_capability(token)},
            ).mappings().first()
            order_row = connection.execute(
                text("""
                    SELECT tenant_id, owner_user_id, status, refundable_balance
                      FROM rof12.orders
                     WHERE order_id = :order_id
                """),
                {"order_id": request.order_id},
            ).mappings().first()
            duplicate = bool(connection.execute(
                text("""
                    SELECT EXISTS(
                        SELECT 1 FROM rof12.refunds
                         WHERE tenant_id = :tenant_id
                           AND operation_id = :operation_id
                    )
                """),
                {"tenant_id": tenant_id, "operation_id": request.operation_id},
            ).scalar())
            system_state = KillSwitch().read(connection)
        capability = None if capability_row is None else CapabilityRecord(
            capability_row["capability_id"],
            capability_row["tenant_id"],
            capability_row["subject_user_id"],
            capability_row["token_hash"],
            CapabilityStatus(capability_row["status"]),
            capability_row["expires_at"],
            Decimal(str(capability_row["max_amount"])),
        )
        verity = evaluate_snapshot(
            dict(order_row) if order_row else None,
            request,
            context,
            capability,
            duplicate,
            now,
        )
        capability_result = validate_capability(capability, request, context, now)
        result = SecurityGate().evaluate(
            context,
            SimpleNamespace(tool_name=proposal.get("tool_name", "")),
            capability_result,
            SimpleNamespace(is_tainted=False),
            SimpleNamespace(risk_level="LOW"),
            verity,
            system_state,
        )
        return result, "postgres_verityflow"
    except MCPError:
        raise
    except (SQLAlchemyError, OSError) as exc:
        raise MCPError("MCP_DATABASE_ERROR", "server-side evaluation failed") from exc


def _response(result: Any, source: str) -> dict[str, Any]:
    return {
        "decision": result.decision.value,
        "reasons": list(result.reasons),
        "dimensions": result.dimensions or {},
        "evaluation_source": source,
    }


@mcp.tool()
def evaluate_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a proposal without executing any tool or issuing authority."""
    result, source = _evaluate_real(proposal)
    return _response(result, source)


@mcp.tool()
def request_permit(proposal: dict[str, Any]) -> dict[str, Any]:
    """Return an opaque permit identifier only after a real ALLOW decision."""
    result, source = _evaluate_real(proposal)
    if result.decision.value != "ALLOW":
        return _response(result, source)
    permit = SecurityGate().mint_if_allowed(result)
    return {
        **_response(result, source),
        "permit_id": permit.permit_id,
        "permit_is_execution_authority": False,
    }


@mcp.tool()
def execute_refund(proposal: dict[str, Any]) -> dict[str, Any]:
    """Revalidate and execute inside one server-side transaction.

    No permit, capability token, or execution authority is returned to MCP.
    """
    database_url, token, tenant_id, user_id = _configured()
    request = _request_from_proposal(proposal)
    context = SimpleNamespace(
        user_id=user_id, tenant_id=tenant_id,
        membership_status="ACTIVE", role="operator",
    )
    now = datetime.now(UTC)
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": tenant_id},
            )
            capability_row = connection.execute(
                text("""
                    SELECT capability_id, tenant_id, subject_user_id, token_hash,
                           status, expires_at, max_amount
                      FROM rof12.capabilities
                     WHERE token_hash = :token_hash AND tenant_id = :tenant_id
                """),
                {"token_hash": hash_capability(token), "tenant_id": tenant_id},
            ).mappings().first()
            capability = None if capability_row is None else CapabilityRecord(
                capability_row["capability_id"], capability_row["tenant_id"],
                capability_row["subject_user_id"], capability_row["token_hash"],
                CapabilityStatus(capability_row["status"]), capability_row["expires_at"],
                Decimal(str(capability_row["max_amount"])),
            )
            result = RefundWorkflow().execute_transaction(
                connection, context, request, capability,
                SimpleNamespace(is_tainted=False),
                SimpleNamespace(risk_level="LOW"), now, token,
            )
            if getattr(result, "decision", None) is not None and result.decision.value != "ALLOW":
                return _response(result, "postgres_verityflow")
            return {"decision": "ALLOW", "executed": True, "evaluation_source": "postgres_verityflow"}
    except MCPError:
        raise
    except PermissionError as exc:
        raise MCPError("EXECUTION_REJECTED", str(exc)) from exc
    except (SQLAlchemyError, OSError) as exc:
        raise MCPError("MCP_DATABASE_ERROR", "server-side execution failed") from exc


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
