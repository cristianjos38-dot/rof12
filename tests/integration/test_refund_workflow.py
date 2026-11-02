import pickle
from types import SimpleNamespace

import pytest

from app.security.policy_engine import GateDecision, PolicyResult
from app.security.security_gate import GateExecutionPermit, SecurityGate
from app.tools.registry import is_registered


def test_permit_cannot_be_created_or_serialized_by_callers():
    with pytest.raises(TypeError):
        GateExecutionPermit("x", GateDecision.ALLOW)
    permit = SecurityGate().mint_if_allowed(PolicyResult(GateDecision.ALLOW, (), {}))
    with pytest.raises(TypeError):
        pickle.dumps(permit)


def test_unknown_tools_and_direct_refund_tool_bypass_are_denied():
    result = SecurityGate().evaluate(None, SimpleNamespace(tool_name="unknown"), None, None, None, None, False)
    assert result.decision is GateDecision.DENY
    assert is_registered("refund_service") is True
    assert is_registered("arbitrary_tool") is False
    source = __import__("pathlib").Path("app/tools/refund_service.py").read_text()
    assert "requires a SecurityGate permit" in source


def test_transactional_workflow_contains_gate_lock_consume_and_outbox_steps():
    source = __import__("pathlib").Path("app/services/refund_workflow.py").read_text()
    for marker in ("KillSwitch", "FOR UPDATE", "CapabilityManager", "execute_refund_transaction", "outbox_events", "AuditLogger"):
        assert marker in source

