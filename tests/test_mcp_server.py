from datetime import UTC, datetime, timedelta
from decimal import Decimal

import sqlalchemy

from rof12.mcp_server import evaluate_proposal, request_permit
from app.security.capability_manager import hash_capability


class _Result:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row


class _Connection:
    def __init__(self, capability, order):
        self.capability = capability
        self.order = order

    def execute(self, statement, _params):
        sql = str(statement)
        if "capabilities" in sql:
            return _Result(self.capability)
        if "orders" in sql:
            return _Result(self.order)
        return _Result()


class _Transaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, *_args):
        return False


class _Engine:
    def __init__(self, connection):
        self.connection = connection

    def begin(self):
        return _Transaction(self.connection)


def _proposal(amount: str) -> dict:
    return {
        "proposal": True,
        "tool_name": "refund_service",
        "args": {
            "order_id": "order_1042",
            "amount": amount,
            "reason": "synthetic MCP evaluation",
            "operation_id": "mcp-test-operation",
        },
    }


def _configure_db(monkeypatch, amount: str):
    token = "mcp-test-token"
    now = datetime.now(UTC)
    capability = {
        "capability_id": "cap-mcp-test",
        "tenant_id": "tenant_001",
        "subject_user_id": "user_001",
        "token_hash": hash_capability(token),
        "status": "ACTIVE",
        "expires_at": now + timedelta(hours=1),
        "max_amount": Decimal("200.00"),
    }
    order = {
        "tenant_id": "tenant_001",
        "owner_user_id": "user_001",
        "status": "PAID",
        "refundable_balance": Decimal("250.00"),
    }
    connection = _Connection(capability, order)
    monkeypatch.setenv("DATABASE_URL", "postgresql://synthetic-db")
    monkeypatch.setenv("ROF12_MCP_CAPABILITY_TOKEN", token)
    monkeypatch.setenv("ROF12_MCP_TENANT_ID", "tenant_001")
    monkeypatch.setenv("ROF12_MCP_USER_ID", "user_001")
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *_args, **_kwargs: _Engine(connection))
    return _proposal(amount)


def test_mcp_real_verityflow_allows_and_mints_permit(monkeypatch):
    proposal = _configure_db(monkeypatch, "150.00")

    evaluation = evaluate_proposal(proposal)
    permit = request_permit(proposal)

    assert evaluation["decision"] == "ALLOW"
    assert evaluation["evaluation_source"] == "postgres_verityflow"
    assert permit["decision"] == "ALLOW"
    assert permit["permit_id"]
    assert permit["permit_is_execution_authority"] is False


def test_mcp_real_verityflow_rejects_without_permit(monkeypatch):
    proposal = _configure_db(monkeypatch, "300.00")

    evaluation = evaluate_proposal(proposal)
    permit = request_permit(proposal)

    assert evaluation["decision"] == "DENY"
    assert evaluation["dimensions"]["constraint"] is False
    assert "CONSTRAINT_FAILED" in evaluation["reasons"]
    assert permit["decision"] == "DENY"
    assert "permit_id" not in permit
