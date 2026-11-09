"""Small local smoke helper for the ROF12 MCP server's pure evaluation path."""

from rof12.mcp_server import evaluate_proposal


def main() -> None:
    proposal = {"tool_name": "refund_service", "args": {"order_id": "order_1042"}}
    print(evaluate_proposal(proposal, "tenant_001", "user_001"))
    print(evaluate_proposal({"tool_name": "drop_database", "args": {}}, "tenant_001", "user_001"))


if __name__ == "__main__":
    main()
