import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import text


def canonical_json(event: dict) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def chain_hash(prev_hash: str, event: dict) -> str:
    return hashlib.sha256((prev_hash + canonical_json(event)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_hash: str
    prev_hash: str


class AuditLogger:
    def append(self, connection, event_id: str, tenant_id: str, event_type: str, actor_user_id: str, payload: dict) -> AuditEvent:
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('rof12.audit_chain'))"))
        row = connection.execute(text("SELECT event_hash FROM rof12.audit_events ORDER BY chain_sequence DESC LIMIT 1 FOR UPDATE")).first()
        previous = row[0] if row else "GENESIS"
        event = {"event_id": event_id, "tenant_id": tenant_id, "event_type": event_type, "actor_user_id": actor_user_id, "payload": payload}
        digest = chain_hash(previous, event)
        connection.execute(text("""
            INSERT INTO rof12.audit_events (event_id, tenant_id, event_type, actor_user_id, payload, prev_hash, event_hash)
            VALUES (:event_id, :tenant_id, :event_type, :actor_user_id, CAST(:payload AS jsonb), :prev_hash, :event_hash)
        """), {"event_id": event_id, "tenant_id": tenant_id, "event_type": event_type, "actor_user_id": actor_user_id,
               "payload": canonical_json(payload), "prev_hash": previous, "event_hash": digest})
        return AuditEvent(event_id, digest, previous)

    def verify(self, rows) -> bool:
        previous = "GENESIS"
        for row in rows:
            event = {"event_id": row["event_id"], "tenant_id": row["tenant_id"], "event_type": row["event_type"], "actor_user_id": row["actor_user_id"], "payload": row["payload"]}
            if row["prev_hash"] != previous or row["event_hash"] != chain_hash(previous, event):
                return False
            previous = row["event_hash"]
        return True

