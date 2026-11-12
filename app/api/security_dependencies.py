from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.api.authentication import AuthenticationError, decode_access_token
from app.api.dependencies import AuthContext, bearer, get_auth_context


def get_security_context(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    origin: str = Header(default=None),
    referer: str = Header(default=None),
) -> AuthContext:
    if context.role != "security_admin":
        raise HTTPException(403, detail="security_admin role required")
    if not origin and not referer:
        raise HTTPException(403, detail="Origin or Referer required")
    try:
        claims = decode_access_token(credentials.credentials if credentials else "")
        issued = datetime.fromtimestamp(int(claims["iat"]), UTC)
    except (AuthenticationError, KeyError, TypeError, ValueError, OSError) as exc:
        raise HTTPException(401, detail="recent authentication required") from exc
    if (datetime.now(UTC) - issued).total_seconds() > 300:
        raise HTTPException(401, detail="recent authentication required")
    return context

