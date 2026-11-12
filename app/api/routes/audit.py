from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import AuthContext, get_auth_context
from app.db.connection import create_app_engine
from app.persistence.audit_logger import AuditLogger

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("/verify")
def verify_audit_chain(context: AuthContext = Depends(get_auth_context)):
    """Verify the tenant-scoped audit chain without exposing event payloads."""
    try:
        with create_app_engine().begin() as connection:
            connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": context.tenant_id})
            rows = connection.execute(text("""
                SELECT event_id, tenant_id, event_type, actor_user_id, payload, prev_hash, event_hash
                  FROM rof12.audit_events
                 ORDER BY chain_sequence ASC
            """)).mappings().all()
            valid = AuditLogger().verify(rows)
    except SQLAlchemyError as exc:
        raise HTTPException(503, detail="audit verification unavailable") from exc
    return {"valid": valid, "event_count": len(rows), "tenant_id": context.tenant_id}
