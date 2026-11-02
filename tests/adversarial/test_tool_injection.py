from types import SimpleNamespace

from app.api.dependencies import AuthContext
from app.security.policy_engine import GateDecision
from app.security.security_gate import SecurityGate


def test_unregistered_tool_is_denied():
    # T-07
    result = SecurityGate().evaluate(AuthContext("u", "t", "operator", "ACTIVE", "u"), SimpleNamespace(tool_name="drop_database"), None, None, None, None, False)
    assert result.decision is GateDecision.DENY
    assert "UNKNOWN_TOOL" in result.reasons

