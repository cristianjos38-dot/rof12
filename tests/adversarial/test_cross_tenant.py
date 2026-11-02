from types import SimpleNamespace

from app.api.dependencies import AuthContext
from app.security.policy_engine import GateDecision, evaluate


def test_cross_tenant_is_denied_without_resource_disclosure():
    # T-01 and T-02
    result = evaluate(AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001"), SimpleNamespace(tool_name="refund_service"), SimpleNamespace(valid=True, reasons=()), SimpleNamespace(is_tainted=False), SimpleNamespace(risk_level="LOW"), SimpleNamespace(checks={"V2": False, "V4": True, "V5": True}), SimpleNamespace(active=False))
    assert result.decision is GateDecision.DENY
    assert "TENANT_MISMATCH" in result.reasons

