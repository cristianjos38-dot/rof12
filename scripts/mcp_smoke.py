"""Small local smoke helper for the ROF12 MCP server's pure evaluation path."""

import os

from rof12.mcp_server import MCPError, evaluate_proposal, request_permit


def main() -> None:
    proposal = {
        "tool_name": "refund_service",
        "args": {
            "order_id": "order_1042",
            "amount": "10.00",
            "reason": "synthetic smoke",
            "operation_id": "mcp-smoke",
        },
    }
    if not all(os.getenv(name) for name in (
        "DATABASE_URL", "ROF12_MCP_CAPABILITY_TOKEN", "ROF12_MCP_TENANT_ID", "ROF12_MCP_USER_ID"
    )):
        for tool in (evaluate_proposal, request_permit):
            try:
                tool(proposal)
            except MCPError as exc:
                print(f"{tool.__name__}: rejected safely ({exc.code})")
            else:  # pragma: no cover - defensive assertion for the smoke itself
                raise SystemExit("MCP smoke unexpectedly evaluated without server configuration")
        return
    print(evaluate_proposal(proposal))
    print(request_permit({**proposal, "tool_name": "drop_database"}))


if __name__ == "__main__":
    main()
