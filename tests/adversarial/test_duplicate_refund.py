from datetime import UTC, datetime
from decimal import Decimal

from app.api.dependencies import AuthContext
from app.domain.contracts import ToolRequest
from app.security.capability_manager import CapabilityRecord, CapabilityStatus
from app.verification.verityflow import VerityReason, evaluate_snapshot


def test_duplicate_operation_is_denied():
    # T-05
    result = evaluate_snapshot({"tenant_id": "tenant_001", "owner_user_id": "user_001", "status": "PAID", "refundable_balance": "250.00"}, ToolRequest(order_id="o", amount=Decimal("1.00"), reason="x", operation_id="same"), AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001"), CapabilityRecord("c", "tenant_001", "user_001", "h", CapabilityStatus.ACTIVE, datetime(2030, 1, 1, tzinfo=UTC), Decimal("200.00")), True, datetime.now(UTC))
    assert VerityReason.DUPLICATE_OPERATION in result.reasons

