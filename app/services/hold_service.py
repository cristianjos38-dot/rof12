from sqlalchemy import text

from app.security.hold_manager import HoldError, HoldStatus


class HoldService:
    """Database-backed hold transitions; approval only succeeds after caller revalidation."""

    def __init__(self, connection):
        self.connection = connection

    def resolve(self, hold_id, ctx, approve: bool, revalidate, justification: str = ""):
        if getattr(ctx, "role", None) not in {"approver", "admin", "security_admin"}:
            raise HoldError("role cannot resolve hold")
        row = self.connection.execute(text("SELECT status, expires_at FROM rof12.holds WHERE hold_id = :id FOR UPDATE"), {"id": hold_id}).mappings().first()
        if not row or row["status"] != HoldStatus.OPEN.value:
            raise HoldError("hold is not open")
        if row["expires_at"] <= __import__("datetime").datetime.now(__import__("datetime").timezone.utc):
            raise HoldError("hold expired")
        if approve:
            result = revalidate()
            if getattr(result, "decision", None) != "ALLOW":
                raise HoldError("revalidation did not allow execution")
            status = HoldStatus.APPROVED.value
        else:
            status = HoldStatus.REJECTED.value
        self.connection.execute(text("""
            UPDATE rof12.holds
               SET status = :status, resolved_by = :user_id, justification = :justification
             WHERE hold_id = :id
        """), {"status": status, "user_id": ctx.user_id, "justification": justification, "id": hold_id})
        from app.persistence.audit_logger import AuditLogger
        AuditLogger().append(
            self.connection, f"hold-resolution:{hold_id}", ctx.tenant_id,
            "HOLD_RESOLUTION", ctx.user_id,
            {"hold_id": hold_id, "status": status, "approver_id": ctx.user_id, "justification": justification},
        )
        return status

