from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from math import isfinite
from typing import Optional

from sqlalchemy import text

from app.security.capability_manager import CapabilityRecord, ReasonCode, validate as validate_capability


class VerityReason(str, Enum):
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    TENANT_MISMATCH = "TENANT_MISMATCH"
    ORDER_STATE_INVALID = "ORDER_STATE_INVALID"
    AMOUNT_EXCEEDS_BALANCE = "AMOUNT_EXCEEDS_BALANCE"
    AMOUNT_EXCEEDS_CAPABILITY = "AMOUNT_EXCEEDS_CAPABILITY"
    DUPLICATE_OPERATION = "DUPLICATE_OPERATION"
    INVALID_AMOUNT = "INVALID_AMOUNT"


@dataclass(frozen=True)
class VerityFlowResult:
    allowed: bool
    reasons: tuple
    checks: dict


VALID_STATES = frozenset({"PAID", "FULFILLED", "REFUNDABLE"})


def _valid_amount(amount) -> bool:
    return isinstance(amount, Decimal) and amount.is_finite() and amount > 0 and amount.as_tuple().exponent >= -2


def evaluate_snapshot(order: Optional[dict], request, ctx, capability: Optional[CapabilityRecord], duplicate: bool, now: datetime) -> VerityFlowResult:
    reasons = []
    checks = {}
    amount = getattr(request, "amount", None)
    checks["V1"] = order is not None
    if order is None:
        reasons.append(VerityReason.ORDER_NOT_FOUND)
    checks["V2"] = order is not None and order.get("tenant_id") == ctx.tenant_id and order.get("owner_user_id") == ctx.user_id
    if not checks["V2"]:
        reasons.append(VerityReason.TENANT_MISMATCH)
    checks["V3"] = order is not None and order.get("status") in VALID_STATES
    if not checks["V3"]:
        reasons.append(VerityReason.ORDER_STATE_INVALID)
    checks["V4"] = _valid_amount(amount) and order is not None and amount <= Decimal(str(order.get("refundable_balance", "0")))
    if not checks["V4"]:
        reasons.append(VerityReason.AMOUNT_EXCEEDS_BALANCE)
    capability_result = validate_capability(capability, request, ctx, now)
    checks["V5"] = capability_result.valid
    if not checks["V5"]:
        reasons.append(VerityReason.AMOUNT_EXCEEDS_CAPABILITY)
    checks["V6"] = not duplicate
    if duplicate:
        reasons.append(VerityReason.DUPLICATE_OPERATION)
    if not _valid_amount(amount):
        reasons.append(VerityReason.INVALID_AMOUNT)
    unique_reasons = tuple(dict.fromkeys(reasons))
    return VerityFlowResult(not unique_reasons, unique_reasons, checks)


def evaluate(connection, request, ctx, capability: Optional[CapabilityRecord], now: datetime) -> VerityFlowResult:
    """Run all six checks under a row lock; this function never calls an AI model."""
    row = connection.execute(text("""
        SELECT tenant_id, owner_user_id, status, refundable_balance
          FROM rof12.orders
         WHERE order_id = :order_id
         FOR UPDATE
    """), {"order_id": request.order_id}).mappings().first()
    duplicate = connection.execute(text("""
        SELECT EXISTS(SELECT 1 FROM rof12.refunds WHERE tenant_id = :tenant_id AND operation_id = :operation_id)
    """), {"tenant_id": ctx.tenant_id, "operation_id": request.operation_id}).scalar()
    return evaluate_snapshot(dict(row) if row else None, request, ctx, capability, bool(duplicate), now)

