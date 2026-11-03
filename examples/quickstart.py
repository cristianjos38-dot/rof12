"""Evaluate two proposals locally with the standalone ROF12 Gate."""
import tempfile

from rof12.audit import Audit
from rof12.gate import Gate, Proposal
from rof12.tools import Store

policy = {
    "tools": {"refunds.create": {"risk": "high", "side_effects": True}},
    "refunds": {"currency": "USD", "auto_allow_max": 100.0, "approval_max": 500.0, "max_age_days": 30},
    "approval": {"hold_ttl_seconds": 900},
    "permit": {"ttl_seconds": 300},
    "grants": {"TKT-1042": {"agent": "support-agent-01", "customer_id": "C-204", "allowed_tools": ["refunds.create"], "max_refund": 500.0, "ttl_seconds": 900}},
}
with tempfile.TemporaryDirectory() as tmp:
    gate = Gate(policy, Store(), Audit(f"{tmp}/audit.jsonl"))
    for amount in (45.0, 1850.0):
        decision = gate.evaluate(Proposal("TKT-1042", "support-agent-01", "refunds.create", {"order_id": "ORD-7731", "amount": amount}))
        print(f"${amount:.2f}: {decision.decision}")
