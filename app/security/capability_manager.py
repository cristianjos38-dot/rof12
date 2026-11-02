from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum

from sqlalchemy import text


class CapabilityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONSUMED = "CONSUMED"
    REVOKED = "REVOKED"


class ReasonCode(str, Enum):
    CAPABILITY_NOT_FOUND = "CAPABILITY_NOT_FOUND"
    CAPABILITY_REVOKED = "CAPABILITY_REVOKED"
    CAPABILITY_CONSUMED = "CAPABILITY_CONSUMED"
    CAPABILITY_EXPIRED = "CAPABILITY_EXPIRED"
    CAPABILITY_TENANT_MISMATCH = "CAPABILITY_TENANT_MISMATCH"
    CAPABILITY_USER_MISMATCH = "CAPABILITY_USER_MISMATCH"
    CAPABILITY_AMOUNT_EXCEEDED = "CAPABILITY_AMOUNT_EXCEEDED"


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    tenant_id: str
    subject_user_id: str
    token_hash: str
    status: CapabilityStatus
    expires_at: datetime
    max_amount: Decimal


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reasons: tuple


def hash_capability(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate(capability: CapabilityRecord | None, request, ctx, now: datetime) -> ValidationResult:
    reasons = []
    if capability is None:
        return ValidationResult(False, (ReasonCode.CAPABILITY_NOT_FOUND,))
    if capability.status is CapabilityStatus.REVOKED:
        reasons.append(ReasonCode.CAPABILITY_REVOKED)
    if capability.status is CapabilityStatus.CONSUMED:
        reasons.append(ReasonCode.CAPABILITY_CONSUMED)
    if capability.expires_at <= now:
        reasons.append(ReasonCode.CAPABILITY_EXPIRED)
    if capability.tenant_id != ctx.tenant_id:
        reasons.append(ReasonCode.CAPABILITY_TENANT_MISMATCH)
    if capability.subject_user_id != ctx.user_id:
        reasons.append(ReasonCode.CAPABILITY_USER_MISMATCH)
    amount = getattr(request, "amount", None)
    if not isinstance(amount, Decimal) or not amount.is_finite() or int(amount.as_tuple().exponent) < -2 or amount <= 0 or amount > capability.max_amount:
        reasons.append(ReasonCode.CAPABILITY_AMOUNT_EXCEEDED)
    return ValidationResult(not reasons, tuple(reasons))


class CapabilityManager:
    def __init__(self, connection):
        self.connection = connection

    def issue(self, tenant_id: str, subject_user_id: str, max_amount: Decimal, ttl: timedelta, scope: str = "refund") -> str:
        token = secrets.token_urlsafe(32)
        capability_id = secrets.token_hex(16)
        expires_at = datetime.now(UTC) + ttl
        self.connection.execute(text("""
            INSERT INTO rof12.capabilities
                (capability_id, tenant_id, subject_user_id, token_hash, scope, max_amount, status, expires_at)
            VALUES (:capability_id, :tenant_id, :subject_user_id, :token_hash, :scope, :max_amount, 'ACTIVE', :expires_at)
        """), {"capability_id": capability_id, "tenant_id": tenant_id, "subject_user_id": subject_user_id,
               "token_hash": hash_capability(token), "scope": scope, "max_amount": max_amount, "expires_at": expires_at})
        return token

    def consume(self, token: str, request, ctx, now: datetime | None = None) -> str | None:
        moment = now or datetime.now(UTC)
        row = self.connection.execute(text("""
            UPDATE rof12.capabilities
               SET status = 'CONSUMED', consumed_at = :now
             WHERE token_hash = :token_hash
               AND tenant_id = :tenant_id
               AND subject_user_id = :user_id
               AND status = 'ACTIVE'
               AND expires_at > :now
               AND max_amount >= :amount
            RETURNING capability_id
        """), {"token_hash": hash_capability(token), "tenant_id": ctx.tenant_id, "user_id": ctx.user_id,
               "amount": request.amount, "now": moment}).first()
        return row[0] if row else None

    def revoke(self, capability_id: str, tenant_id: str) -> None:
        self.connection.execute(text("UPDATE rof12.capabilities SET status = 'REVOKED' WHERE capability_id = :id AND tenant_id = :tenant_id"), {"id": capability_id, "tenant_id": tenant_id})

    def revoke_tenant(self, tenant_id: str) -> None:
        self.connection.execute(text("UPDATE rof12.capabilities SET status = 'REVOKED' WHERE tenant_id = :tenant_id AND status = 'ACTIVE'"), {"tenant_id": tenant_id})

