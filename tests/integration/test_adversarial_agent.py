

from pydantic import ValidationError

from app.agents.model_router import ModelRouter
from app.api.dependencies import AuthContext
from app.domain.contracts import ToolRequest
from app.security.policy_engine import GateDecision, PolicyResult
from app.security.security_gate import SecurityGate


def test_mock_adversarial_requests_cannot_reach_allow():
    router = ModelRouter(mode="mock_adversarial")
    context = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
    gate = SecurityGate()
    for payload in router.adversarial_requests():
        try:
            request = ToolRequest.model_validate(payload)
        except ValidationError:
            continue
        result = gate.evaluate(context, request, PolicyResult(GateDecision.DENY, ("adversarial",), {}), None, None, type("V", (), {"checks": {"V2": True, "V4": False, "V5": False}})(), False)
        assert result.decision in {GateDecision.DENY, GateDecision.QUARANTINE}

