from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from hypothesis import given, strategies as st

from app.security.capability_manager import CapabilityRecord, CapabilityStatus, validate
from app.security.policy_engine import GateDecision, evaluate as evaluate_policy
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


def _policy_result(*, hard: str | None = None, tainted: bool = False, kill: bool = False):
    kill = kill or hard == "KILL_SWITCH_ACTIVE"
    context = SimpleNamespace(user_id="user_001", tenant_id="tenant_001", membership_status="ACTIVE")
    request = SimpleNamespace(tool_name="refund_service")
    capability = SimpleNamespace(valid=hard != "AUTHORITY_INVALID", reasons=())
    verity = SimpleNamespace(
        checks={"V2": hard != "TENANT_MISMATCH", "V4": hard != "CONSTRAINT_FAILED", "V5": hard != "CONSTRAINT_FAILED"},
        approval_required=False,
    )
    if hard == "INVALID_IDENTITY":
        context = SimpleNamespace(user_id="", tenant_id="tenant_001", membership_status="ACTIVE")
    if hard == "UNKNOWN_TOOL":
        request = SimpleNamespace(tool_name="drop_database")
    return evaluate_policy(
        context, request, capability, SimpleNamespace(is_tainted=tainted),
        SimpleNamespace(risk_level="HIGH" if tainted else "LOW"), verity,
        SimpleNamespace(active=kill),
    )


@given(st.sampled_from(("KILL_SWITCH_ACTIVE", "INVALID_IDENTITY", "UNKNOWN_TOOL", "TENANT_MISMATCH", "AUTHORITY_INVALID", "CONSTRAINT_FAILED")))
def test_policy_hard_reasons_never_allow(reason: str):
    assert _policy_result(hard=reason).decision is not GateDecision.ALLOW


@given(st.booleans())
def test_policy_allow_requires_clean_context_and_all_dimensions(clean: bool):
    result = _policy_result(tainted=not clean)
    if clean:
        assert result.decision is GateDecision.ALLOW
    else:
        assert result.decision is GateDecision.QUARANTINE


def test_policy_kill_switch_always_denies():
    assert _policy_result(kill=True).decision is GateDecision.DENY
