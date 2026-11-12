from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from hypothesis import given, strategies as st

from app.security.capability_manager import CapabilityRecord, CapabilityStatus, validate
from rof12.attack_round import AuditChain


@given(st.decimals(min_value="0.01", max_value="200.00", places=2, allow_nan=False, allow_infinity=False))
def test_decimal_money_is_preserved_without_float_rounding(amount: Decimal):
    assert isinstance(amount, Decimal)
    assert amount.as_tuple().exponent >= -2
    assert amount == Decimal(str(amount))


@given(st.integers(min_value=1, max_value=3600))
def test_capability_expiry_is_strict(seconds: int):
    now = datetime(2030, 1, 1, tzinfo=UTC)
    capability = CapabilityRecord("c", "tenant_001", "user_001", "hash", CapabilityStatus.ACTIVE, now + timedelta(seconds=seconds), Decimal("200.00"))
    request = SimpleNamespace(amount=Decimal("1.00"))
    ctx = SimpleNamespace(tenant_id="tenant_001", user_id="user_001")
    assert validate(capability, request, ctx, now).valid
    assert not validate(capability, request, ctx, capability.expires_at).valid


def test_audit_chain_detects_any_link_tampering():
    chain = AuditChain()
    chain.append({"decision": "ALLOW"})
    chain.append({"decision": "DENY"})
    chain.records[1]["decision"] = "ALLOW"
    assert not chain.verify()
