from datetime import UTC, datetime
from decimal import Decimal

from app.api.dependencies import AuthContext
from app.domain.contracts import ToolRequest
from app.security.capability_manager import (
    CapabilityRecord,
    CapabilityStatus,
    ReasonCode,
    validate,
)


def test_capability_amount_escalation_denied():
    # T-09
    record = CapabilityRecord("c", "tenant_001", "user_001", "hash", CapabilityStatus.ACTIVE, datetime.now(UTC), Decimal("50.00"))
    request = ToolRequest(order_id="order_1042", amount=Decimal("150.00"), reason="x", operation_id="op")
    result = validate(record, request, AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001"), datetime.now(UTC))
    assert ReasonCode.CAPABILITY_AMOUNT_EXCEEDED in result.reasons

