from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.persistence.audit_logger import AuditLogger, chain_hash
from app.security.hold_manager import Hold, HoldError, HoldManager, HoldStatus
from app.security.kill_switch import KillSwitch, KillSwitchError

NOW = datetime.now(UTC)


def test_hold_requires_approver_and_revalidates_before_approval():
    manager = HoldManager()
    manager.open(Hold("h1", "tenant_001", "user_001", NOW + timedelta(hours=1)))
    with pytest.raises(HoldError):
        manager.resolve("h1", SimpleNamespace(role="operator"), NOW, True, lambda: SimpleNamespace(decision="ALLOW"))
    with pytest.raises(HoldError):
        manager.resolve("h1", SimpleNamespace(role="approver"), NOW, True, lambda: SimpleNamespace(decision="DENY"))
    hold = manager.resolve("h1", SimpleNamespace(role="approver"), NOW, True, lambda: SimpleNamespace(decision="ALLOW"))
    assert hold.status is HoldStatus.APPROVED


def test_hold_expiration_and_kill_switch_role():
    manager = HoldManager()
    manager.open(Hold("h2", "tenant_001", "user_001", NOW - timedelta(seconds=1)))
    with pytest.raises(HoldError):
        manager.resolve("h2", SimpleNamespace(role="approver"), NOW, True, lambda: SimpleNamespace(decision="ALLOW"))
    class Connection:
        def __init__(self): self.calls = []
        def execute(self, statement, params=None): self.calls.append(str(statement)); return SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: None))
    with pytest.raises(KillSwitchError):
        KillSwitch().activate(Connection(), SimpleNamespace(role="operator"), "incident")


def test_audit_chain_detects_tampering_and_uses_advisory_lock_sql():
    previous = "GENESIS"
    event = {"event_id": "e1", "tenant_id": "tenant_001", "event_type": "X", "actor_user_id": "user_001", "payload": {"ok": True}}
    digest = chain_hash(previous, event)
    logger = AuditLogger()
    assert logger.verify(({**event, "prev_hash": previous, "event_hash": digest},)) is True
    assert logger.verify(({**event, "prev_hash": previous, "event_hash": "tampered"},)) is False
    source = __import__("pathlib").Path("app/persistence/audit_logger.py").read_text()
    assert "pg_advisory_xact_lock" in source

