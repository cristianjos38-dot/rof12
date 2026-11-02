from types import SimpleNamespace

from app.api.dependencies import AuthContext
from app.security.policy_engine import GateDecision, evaluate


def test_kill_switch_cannot_be_bypassed():
    # T-10
    result = evaluate(AuthContext("u", "t", "operator", "ACTIVE", "u"), SimpleNamespace(tool_name="refund_service"), SimpleNamespace(valid=True, reasons=()), SimpleNamespace(is_tainted=False), SimpleNamespace(risk_level="LOW"), SimpleNamespace(checks={"V2": True, "V4": True, "V5": True}), SimpleNamespace(active=True))
    assert result.decision is GateDecision.DENY
    assert "KILL_SWITCH_ACTIVE" in result.reasons

