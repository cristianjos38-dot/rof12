
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_PUBLIC_KEY,
    JWT_SECRET,
)

REQUIRED_CLAIMS = frozenset({"sub", "iss", "aud", "exp", "iat"})
OPTIONAL_CLAIMS = frozenset({"agent_id"})


class AuthenticationError(ValueError):
    pass


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            JWT_PUBLIC_KEY or JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["sub", "iss", "aud", "exp", "iat"]},
        )
    except ExpiredSignatureError as exc:
        raise AuthenticationError("token expired") from exc
    except InvalidTokenError as exc:
        raise AuthenticationError("invalid token") from exc

    if not REQUIRED_CLAIMS.issubset(claims) or set(claims) - REQUIRED_CLAIMS - OPTIONAL_CLAIMS:
        raise AuthenticationError("token contains unauthorized claims")
    if not isinstance(claims["sub"], str) or not claims["sub"]:
        raise AuthenticationError("token subject must be a non-empty user id")
    if "agent_id" in claims and (not isinstance(claims["agent_id"], str) or not claims["agent_id"]):
        raise AuthenticationError("agent_id must be a non-empty identifier")
    return claims

