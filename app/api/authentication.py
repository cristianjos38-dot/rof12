
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.config import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_PUBLIC_KEY,
    JWT_SECRET,
)

ALLOWED_CLAIMS = frozenset({"sub", "iss", "aud", "exp", "iat"})


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

    if set(claims) != ALLOWED_CLAIMS:
        raise AuthenticationError("token contains unauthorized claims")
    if not isinstance(claims["sub"], str) or not claims["sub"]:
        raise AuthenticationError("token subject must be a non-empty user id")
    return claims

