from types import SimpleNamespace

from app.domains.devops_approval import DeploymentProposal, evaluate_deployment


CTX = SimpleNamespace(user_id="user_001", tenant_id="tenant_001", membership_status="ACTIVE")


def test_devops_legitimate_deployment_is_allowed():
    result = evaluate_deployment(DeploymentProposal("api", "sha256:" + "a" * 64, "staging", "CHG-001"), context=CTX, approved_ticket="CHG-001")
    assert result.decision.value == "ALLOW"


def test_devops_attacks_are_denied():
    cases = [
        DeploymentProposal("api", "latest", "staging", "CHG-001"),
        DeploymentProposal("api", "sha256:abc", "production", "CHG-999"),
        DeploymentProposal("api", "sha256:abc", "staging", "CHG-999"),
        DeploymentProposal("api", "sha256:tampered", "staging", "CHG-001"),
    ]
    for proposal in cases:
        assert evaluate_deployment(proposal, context=CTX, approved_ticket="CHG-001").decision.value == "DENY"
