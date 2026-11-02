import pytest

from app.provenance import (
    ProvenanceTracker,
    ReconciliationError,
    SourceRegistry,
    TaintedValue,
    TrustLevel,
)


def test_external_values_start_tainted_and_untrusted():
    value = ProvenanceTracker().extract("order_1042", "doc-1", "invoice", "hash")
    assert value.is_tainted is True
    assert value.trust_level is TrustLevel.UNTRUSTED


def test_taint_propagates_through_arithmetic_and_transforms():
    tainted = TaintedValue.external(10, "doc-1")
    result = (tainted + 5).transform(lambda x: x * 2)
    assert result.value == 30
    assert result.is_tainted is True
    assert result.trust_level is TrustLevel.UNTRUSTED


def test_exact_reconciliation_is_the_only_detainter():
    tracker = ProvenanceTracker(SourceRegistry())
    tainted = tracker.extract("order_1042", "doc-1")
    trusted = tracker.reconcile(tainted, "order_1042")
    assert trusted.is_tainted is False
    assert trusted.trust_level is TrustLevel.FULLY_RECONCILED
    with pytest.raises(ReconciliationError):
        tracker.reconcile(tainted, "order_9999")

