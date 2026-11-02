import datetime as dt

import jwt
import pytest

from app.api.authentication import AuthenticationError, decode_access_token
from app.config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET


def token(**overrides):
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": "user_001", "iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "exp": now + dt.timedelta(minutes=5), "iat": now}
    payload.update(overrides)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_valid_token_has_only_authorized_claims():
    assert decode_access_token(token())["sub"] == "user_001"


def test_tenant_and_roles_claims_are_rejected():
    with pytest.raises(AuthenticationError):
        decode_access_token(token(tenant_id="tenant_001"))
    with pytest.raises(AuthenticationError):
        decode_access_token(token(roles=["admin"]))


def test_bad_signature_and_expiration_are_rejected():
    bad_signature = jwt.encode({"sub": "user_001", "iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "exp": 9999999999, "iat": 1}, "wrong-secret-32-bytes-long-value", algorithm=JWT_ALGORITHM)
    with pytest.raises(AuthenticationError):
        decode_access_token(bad_signature)
    with pytest.raises(AuthenticationError):
        decode_access_token(token(exp=dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)))

