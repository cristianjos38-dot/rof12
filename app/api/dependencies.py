from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.api.authentication import AuthenticationError, decode_access_token
from app.db.connection import create_app_engine


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    tenant_id: str
    role: str
    membership_status: str
    token_sub: str
    agent_id: str | None = None


bearer = HTTPBearer(auto_error=False)
RLS_SET_LOCAL_SQL = "SET LOCAL app.tenant_id = :tenant_id"


def _set_local_tenant(connection, tenant_id: str) -> None:
    # Parameterized set_config is PostgreSQL's safe equivalent of:
    # SET LOCAL app.tenant_id = :tenant_id
    connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})


def resolve_auth_context(claims: dict, connection, tenant_selector: Optional[str]) -> AuthContext:
    user_id = claims["sub"]
    if not tenant_selector:
        raise AuthenticationError("X-Tenant-ID is required to select an active membership")
    _set_local_tenant(connection, tenant_selector)
    row = connection.execute(
        text("""
            SELECT m.tenant_id, m.role, m.status
            FROM rof12.memberships AS m
            JOIN rof12.users AS u ON u.tenant_id = m.tenant_id AND u.user_id = m.user_id
            WHERE m.tenant_id = :tenant_id AND m.user_id = :user_id
              AND m.status = 'ACTIVE' AND u.status = 'ACTIVE'
            ORDER BY m.role
            LIMIT 1
        """),
        {"tenant_id": tenant_selector, "user_id": user_id},
    ).mappings().first()
    if row is None:
        raise AuthenticationError("no active membership for requested tenant")
    return AuthContext(user_id=user_id, tenant_id=row["tenant_id"], role=row["role"], membership_status=row["status"], token_sub=user_id, agent_id=claims.get("agent_id"))


def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    tenant_selector: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
) -> AuthContext:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        claims = decode_access_token(credentials.credentials)
        engine = create_app_engine()
        with engine.begin() as connection:
            context = resolve_auth_context(claims, connection, tenant_selector)
            request.state.auth_context = context
            return context
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

