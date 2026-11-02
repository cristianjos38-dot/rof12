from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.api.dependencies import AuthContext
from app.domain.contracts import ToolRequest
from app.security.capability_manager import (
    CapabilityRecord,
    CapabilityStatus,
    ReasonCode,
    hash_capability,
    validate,
)

CTX = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
NOW = datetime.now(UTC)
REQ = ToolRequest(order_id="order_1042", amount=Decimal("100.00"), reason="refund", operation_id="op")


def record(status=CapabilityStatus.ACTIVE, expires=None, tenant="tenant_001", user="user_001", amount="200.00"):
    return CapabilityRecord("cap-1", tenant, user, hash_capability("token"), status, expires or NOW + timedelta(hours=1), Decimal(amount))


def test_validate_is_pure_and_accumulates_reasons():
    result = validate(record(), REQ, CTX, NOW)
    assert result.valid is True and result.reasons == ()
    failed = validate(record(CapabilityStatus.REVOKED, NOW - timedelta(seconds=1), "tenant_002", "user_002", "50.00"), REQ, CTX, NOW)
    assert set(failed.reasons) == {ReasonCode.CAPABILITY_REVOKED, ReasonCode.CAPABILITY_EXPIRED, ReasonCode.CAPABILITY_TENANT_MISMATCH, ReasonCode.CAPABILITY_USER_MISMATCH, ReasonCode.CAPABILITY_AMOUNT_EXCEEDED}

