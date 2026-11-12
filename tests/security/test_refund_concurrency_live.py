from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text

from app.domain.contracts import ToolRequest
from app.security.capability_manager import hash_capability
from app.services.refund_workflow import RefundWorkflow
from app.api.dependencies import AuthContext


pytestmark = pytest.mark.skipif(
    not (os.getenv("DATABASE_OWNER_URL") and os.getenv("ROF12_EXECUTOR_DB_URL")),
    reason="live owner and executor PostgreSQL URLs are required",
)


def test_same_capability_and_operation_have_one_live_winner():
    owner_engine = create_engine(os.environ["DATABASE_OWNER_URL"])
    executor_url = os.environ["ROF12_EXECUTOR_DB_URL"]
    operation_id = "live-race-operation"
    token = "live-race-capability"
    with owner_engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO rof12.orders (tenant_id, order_id, owner_user_id, status, refundable_balance)
            VALUES ('tenant_001', 'live-race-order', 'user_001', 'PAID', 250.00)
            ON CONFLICT (tenant_id, order_id) DO UPDATE SET refundable_balance = 250.00
        """))
        connection.execute(text("DELETE FROM rof12.refunds WHERE tenant_id = 'tenant_001' AND operation_id = :operation_id"), {"operation_id": operation_id})
        connection.execute(text("""
            INSERT INTO rof12.capabilities
              (capability_id, tenant_id, subject_user_id, token_hash, scope, max_amount, status, expires_at)
            VALUES ('live-race-capability', 'tenant_001', 'user_001', :token_hash, 'refund', 200.00, 'ACTIVE', :expires)
            ON CONFLICT (capability_id) DO UPDATE SET token_hash = EXCLUDED.token_hash, status = 'ACTIVE', expires_at = EXCLUDED.expires_at
        """), {"token_hash": hash_capability(token), "expires": datetime.now(UTC) + timedelta(minutes=5)})

    def attempt(_index: int) -> str:
        engine = create_engine(executor_url, pool_pre_ping=True)
        context = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
        request = ToolRequest(order_id="live-race-order", amount=Decimal("10.00"), reason="live race", operation_id=operation_id)
        with engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', 'tenant_001', true)"))
            row = connection.execute(text("SELECT capability_id, tenant_id, subject_user_id, token_hash, status, expires_at, max_amount FROM rof12.capabilities WHERE capability_id = 'live-race-capability'" )).mappings().first()
            from app.security.capability_manager import CapabilityRecord, CapabilityStatus
            capability = CapabilityRecord(row["capability_id"], row["tenant_id"], row["subject_user_id"], row["token_hash"], CapabilityStatus(row["status"]), row["expires_at"], Decimal(str(row["max_amount"])))
            result = RefundWorkflow().execute_transaction(connection, context, request, capability, type("P", (), {"is_tainted": False})(), type("R", (), {"risk_level": "LOW"})(), datetime.now(UTC), token)
            decision = getattr(result, "decision", None)
            return "EXECUTED" if decision is not None and decision.value == "ALLOW" else decision.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, (1, 2)))
    assert outcomes.count("EXECUTED") == 1
    assert sum(item in {"DENY", "EXECUTED"} for item in outcomes) == 2
