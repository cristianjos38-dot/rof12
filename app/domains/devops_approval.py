"""Second-domain deployment approval through the same SecurityGate."""

from dataclasses import dataclass
from types import SimpleNamespace

from app.security.security_gate import SecurityGate


@dataclass(frozen=True)
class DeploymentProposal:
    service: str
    image_digest: str
    environment: str
    approval_ticket: str


def evaluate_deployment(proposal: DeploymentProposal, *, context, approved_ticket: str):
    digest = proposal.image_digest.removeprefix("sha256:")
    valid = bool(len(digest) == 64 and all(char in "0123456789abcdef" for char in digest) and proposal.approval_ticket == approved_ticket)
    return SecurityGate().evaluate(
        context,
        SimpleNamespace(tool_name="deployment_approval"),
        SimpleNamespace(valid=valid, reasons=() if valid else ("DEPLOYMENT_AUTHORITY_INVALID",)),
        SimpleNamespace(is_tainted=False),
        SimpleNamespace(risk_level="LOW"),
        SimpleNamespace(checks={"V2": True, "V4": valid, "V5": valid}),
        SimpleNamespace(active=False),
    )
