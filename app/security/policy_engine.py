from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GateDecision(str, Enum):
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    ALLOW = "ALLOW"


@dataclass(frozen=True)
class PolicyResult:
    decision: GateDecision = GateDecision.DENY
    reasons: tuple = ()
    dimensions: dict | None = None


def evaluate(ctx, request, capability, provenance, risk_report, verity_result, system_state) -> PolicyResult:
    """Pure, default-deny policy evaluation. It performs no I/O."""
    reasons = []
    dimensions = {}
    kill_active = bool(getattr(system_state, "active", system_state is True))
    dimensions["kill_switch"] = not kill_active
    if kill_active:
        reasons.append("KILL_SWITCH_ACTIVE")

    identity_ok = bool(ctx and getattr(ctx, "user_id", "") and getattr(ctx, "tenant_id", "") and getattr(ctx, "membership_status", "ACTIVE") == "ACTIVE")
    dimensions["identity"] = identity_ok
    if not identity_ok:
        reasons.append("INVALID_IDENTITY")

    tool_name = getattr(request, "tool_name", "refund_service")
    action_ok = tool_name == "refund_service"
    dimensions["action"] = action_ok
    if not action_ok:
        reasons.append("UNKNOWN_TOOL")

    resource_ok = bool(getattr(verity_result, "checks", {}).get("V2", False))
    dimensions["resource"] = resource_ok
    if not resource_ok:
        reasons.append("TENANT_MISMATCH")

    authority_ok = bool(getattr(capability, "valid", False))
    if hasattr(capability, "reasons"):
        authority_ok = authority_ok and not capability.reasons
    dimensions["authority"] = authority_ok
    if not authority_ok:
        reasons.append("AUTHORITY_INVALID")

    checks = getattr(verity_result, "checks", {}) or {}
    constraint_ok = bool(checks.get("V4", False) and checks.get("V5", False))
    dimensions["constraint"] = constraint_ok
    if not constraint_ok:
        reasons.append("CONSTRAINT_FAILED")

    tainted = bool(getattr(provenance, "is_tainted", False)) or str(getattr(getattr(risk_report, "risk_level", "LOW"), "value", getattr(risk_report, "risk_level", "LOW"))) in {"HIGH", "CRITICAL"}
    dimensions["context_tainting"] = not tainted
    if tainted:
        reasons.append("UNRECONCILED_CONTEXT")

    if reasons:
        # Hard failures take precedence over quarantine and approval.
        hard = {"KILL_SWITCH_ACTIVE", "INVALID_IDENTITY", "UNKNOWN_TOOL", "TENANT_MISMATCH", "AUTHORITY_INVALID", "CONSTRAINT_FAILED"}
        decision = GateDecision.DENY if any(reason in hard for reason in reasons) else GateDecision.QUARANTINE
    elif getattr(verity_result, "approval_required", False):
        decision = GateDecision.REQUIRE_APPROVAL
    else:
        decision = GateDecision.ALLOW
    return PolicyResult(decision, tuple(dict.fromkeys(reasons)), dimensions)

