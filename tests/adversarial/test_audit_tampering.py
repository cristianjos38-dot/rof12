from app.persistence.audit_logger import AuditLogger, chain_hash


def test_audit_verifier_identifies_tampered_event():
    # T-11
    event = {"event_id": "e1", "tenant_id": "t", "event_type": "X", "actor_user_id": "u", "payload": {"amount": "1.00"}}
    digest = chain_hash("GENESIS", event)
    assert AuditLogger().verify(({**event, "prev_hash": "GENESIS", "event_hash": digest},)) is True
    assert AuditLogger().verify(({**event, "prev_hash": "GENESIS", "event_hash": "bad"},)) is False

