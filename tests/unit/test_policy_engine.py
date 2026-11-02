from types import SimpleNamespace

from app.api.dependencies import AuthContext
from app.security.policy_engine import GateDecision, evaluate


CTX = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
CAP = SimpleNamespace(valid=True, reasons=())
VERITY = SimpleNamespace(checks={"V2": True, "V4": True, "V5": True}, approval_required=False)
PROVENANCE = SimpleNamespace(is_tainted=False)
RISK = SimpleNamespace(risk_level="LOW")


def test_policy_allows_only_when_every_dimension_is_positive():
    result = evaluate(CTX, SimpleNamespace(tool_name="refund_service"), CAP, PROVENANCE, RISK, VERITY, SimpleNamespace(active=False))
    assert result.decision is GateDecision.ALLOW
    assert all(result.dimensions.values())


def test_policy_mutations_are_default_deny_or_quarantine():
    mutations = [
        (SimpleNamespace(active=True), GateDecision.DENY),
        (SimpleNamespace(user_id="", tenant_id="tenant_001", membership_status="ACTIVE"), GateDecision.DENY),
        (SimpleNamespace(tool_name="unknown"), GateDecision.DENY),
        (SimpleNamespace(valid=False, reasons=("bad",)), GateDecision.DENY),
        (SimpleNamespace(active=False), GateDecision.QUARANTINE),
    ]
    for mutated_state, expected in mutations:
        ctx = CTX
        request = SimpleNamespace(tool_name="refund_service")
        cap = CAP
        provenance = PROVENANCE
        state = mutated_state
        if hasattr(mutated_state, "user_id"):
            ctx = mutated_state
        elif hasattr(mutated_state, "tool_name"):
            request = mutated_state
        elif hasattr(mutated_state, "valid"):
            cap = mutated_state
        elif mutated_state.active:
            state = mutated_state
        else:
            provenance = SimpleNamespace(is_tainted=True)
        assert evaluate(ctx, request, cap, provenance, RISK, VERITY, state).decision is expected


def test_policy_has_no_approval_authority_from_taint_or_risk():
    result = evaluate(CTX, SimpleNamespace(tool_name="refund_service"), CAP, SimpleNamespace(is_tainted=True), RISK, VERITY, SimpleNamespace(active=False))
    assert result.decision is GateDecision.QUARANTINE
    assert result.decision is not GateDecision.ALLOW

