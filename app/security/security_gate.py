import secrets

from app.security.policy_engine import GateDecision, PolicyResult, evaluate
from app.observability import observe_decision
from app.tools.registry import is_registered

_PERMIT_TOKEN = object()


class GateExecutionPermit:
    __slots__ = ("_internal", "decision", "permit_id")

    def __init__(self, permit_id, decision, _internal=None):
        if _internal is not _PERMIT_TOKEN:
            raise TypeError("GateExecutionPermit is minted only by SecurityGate")
        self.permit_id = permit_id
        self.decision = decision
        self._internal = _internal

    def __reduce__(self):
        raise TypeError("GateExecutionPermit is not serializable")

    def __reduce_ex__(self, protocol):
        raise TypeError("GateExecutionPermit is not serializable")

    def _assert_internal(self):
        if self._internal is not _PERMIT_TOKEN or self.decision is not GateDecision.ALLOW:
            raise PermissionError("invalid execution permit")


class SecurityGate:
    def _mint(self, result: PolicyResult) -> GateExecutionPermit:
        if result.decision is not GateDecision.ALLOW:
            raise PermissionError("cannot mint permit for non-ALLOW decision")
        return GateExecutionPermit(secrets.token_hex(16), result.decision, _PERMIT_TOKEN)

    def evaluate(self, ctx, request, capability, provenance, risk_report, verity_result, system_state):
        if not is_registered(getattr(request, "tool_name", "refund_service")):
            result = PolicyResult(GateDecision.DENY, ("UNKNOWN_TOOL",), {"action": False})
            observe_decision(ctx, result)
            return result
        result = evaluate(ctx, request, capability, provenance, risk_report, verity_result, system_state)
        observe_decision(ctx, result)
        return result

    def mint_if_allowed(self, result: PolicyResult) -> GateExecutionPermit:
        return self._mint(result)

