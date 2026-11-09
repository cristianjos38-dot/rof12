"""Small local smoke helper for the ROF12 MCP server's pure evaluation path."""

import os

from rof12.mcp_server import evaluate_proposal


def main() -> None:
    os.environ.setdefault("ROF12_MCP_TENANT_ID", "tenant_001")
    os.environ.setdefault("ROF12_MCP_USER_ID", "user_001")
    proposal = {"tool_name": "refund_service", "args": {"order_id": "order_1042"}}
    print(evaluate_proposal(proposal))
    print(evaluate_proposal({"tool_name": "drop_database", "args": {}}))


if __name__ == "__main__":
    main()
