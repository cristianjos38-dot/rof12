from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.authentication import AuthenticationError, decode_access_token
from app.api.dependencies import AuthContext, bearer, get_auth_context


def get_security_context(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    origin: str = Header(default=None),
    referer: str = Header(default=None),
    csrf_token: str = Header(default=None, alias="X-CSRF-Token"),
) -> AuthContext:
    if context.role != "security_admin":
        raise HTTPException(403, detail="security_admin role required")
    if not origin and not referer:
        raise HTTPException(403, detail="Origin or Referer required")
    if not csrf_token or csrf_token != request.headers.get("X-Request-ID"):
        raise HTTPException(403, detail="CSRF validation failed")
    try:
        claims = decode_access_token(credentials.credentials if credentials else "")
        issued = datetime.fromtimestamp(int(claims["iat"]), timezone.utc)
    except (AuthenticationError, KeyError, TypeError, ValueError, OSError) as exc:
        raise HTTPException(401, detail="recent authentication required") from exc
    if (datetime.now(timezone.utc) - issued).total_seconds() > 300:
        raise HTTPException(401, detail="recent authentication required")
    return context

