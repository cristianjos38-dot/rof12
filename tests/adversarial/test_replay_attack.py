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


def test_consumed_capability_replay_denied():
    # T-05
    result = validate(CapabilityRecord("c", "tenant_001", "user_001", "hash", CapabilityStatus.CONSUMED, datetime.now(UTC), Decimal("200.00")), ToolRequest(order_id="o", amount=Decimal("1.00"), reason="x", operation_id="op"), AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001"), datetime.now(UTC))
    assert ReasonCode.CAPABILITY_CONSUMED in result.reasons

