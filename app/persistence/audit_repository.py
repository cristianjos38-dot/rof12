from __future__ import annotations

from app.persistence.audit_logger import AuditEvent, AuditLogger


class SQLAlchemyAuditRepository:
    """Audit repository bound to the caller's transaction and tenant session."""

    def __init__(self, connection):
        self.connection = connection
        self.logger = AuditLogger()

    def append(self, event_id: str, tenant_id: str, event_type: str, actor_user_id: str, payload: dict) -> AuditEvent:
        return self.logger.append(self.connection, event_id, tenant_id, event_type, actor_user_id, payload)
