from types import SimpleNamespace

import pytest

from app.provenance import ProvenanceTracker, ReconciliationError
from app.security.policy_engine import GateDecision, evaluate


def test_precision_and_taint_cannot_authorize_execution():
    # T-03 and T-06
    candidate = ProvenanceTracker().extract("Q900.001", "doc-1")
    with pytest.raises(ReconciliationError):
        ProvenanceTracker().reconcile(candidate, "Q900.00")
    result = evaluate(SimpleNamespace(user_id="u", tenant_id="t", membership_status="ACTIVE"), SimpleNamespace(tool_name="refund_service"), SimpleNamespace(valid=True, reasons=()), candidate, SimpleNamespace(risk_level="LOW"), SimpleNamespace(checks={"V2": True, "V4": False, "V5": False}), SimpleNamespace(active=False))
    assert result.decision in {GateDecision.QUARANTINE, GateDecision.DENY}

