from datetime import datetime, timezone
from decimal import Decimal

from app.api.dependencies import AuthContext
from app.domain.contracts import ToolRequest
from app.security.capability_manager import CapabilityRecord, CapabilityStatus
from app.verification.verityflow import VerityReason, evaluate_snapshot


NOW = datetime.now(timezone.utc)
CTX = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")


def request(amount="150.00", operation="op-1"):
    return ToolRequest(order_id="order_1042", amount=Decimal(amount), reason="refund", operation_id=operation)


def capability(amount="200.00"):
    return CapabilityRecord("cap-1", "tenant_001", "user_001", "hash", CapabilityStatus.ACTIVE, NOW.replace(year=2030), Decimal(amount))


def test_verityflow_allows_valid_order():
    result = evaluate_snapshot({"tenant_id": "tenant_001", "owner_user_id": "user_001", "status": "PAID", "refundable_balance": "250.00"}, request(), CTX, capability(), False, NOW)
    assert result.allowed is True
    assert set(result.checks) == {"V1", "V2", "V3", "V4", "V5", "V6"}


def test_verityflow_accumulates_all_failures():
    class InvalidRequest:
        order_id = "order_1042"
        amount = Decimal("-1.000")
        operation_id = "op-1"
    result = evaluate_snapshot(None, InvalidRequest(), CTX, None, True, NOW)
    assert result.allowed is False
    assert VerityReason.ORDER_NOT_FOUND in result.reasons
    assert VerityReason.TENANT_MISMATCH in result.reasons
    assert VerityReason.ORDER_STATE_INVALID in result.reasons
    assert VerityReason.AMOUNT_EXCEEDS_BALANCE in result.reasons
    assert VerityReason.AMOUNT_EXCEEDS_CAPABILITY in result.reasons
    assert VerityReason.DUPLICATE_OPERATION in result.reasons
    assert VerityReason.INVALID_AMOUNT in result.reasons


def test_verityflow_rejects_precision_and_nan():
    order = {"tenant_id": "tenant_001", "owner_user_id": "user_001", "status": "PAID", "refundable_balance": "250.00"}
    for amount in ("10.001", "NaN", "Infinity"):
        class InvalidRequest:
            order_id = "order_1042"
            operation_id = "op-1"
            pass
        invalid_request = InvalidRequest()
        invalid_request.amount = Decimal(amount)
        result = evaluate_snapshot(order, invalid_request, CTX, capability(), False, NOW)
        assert VerityReason.INVALID_AMOUNT in result.reasons

