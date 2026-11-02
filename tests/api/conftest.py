from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import AuthContext, get_auth_context
from app.main import app


@pytest.fixture
def client():
    context = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
    app.dependency_overrides[get_auth_context] = lambda: context
    with TestClient(app, client=(f"test-{uuid4().hex}", 50000)) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def security_client():
    from app.api.security_dependencies import get_security_context
    context = AuthContext("user_admin", "tenant_001", "security_admin", "ACTIVE", "user_admin")
    app.dependency_overrides[get_auth_context] = lambda: context
    app.dependency_overrides[get_security_context] = lambda: context
    with TestClient(app, client=(f"security-{uuid4().hex}", 50001)) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def approver_client():
    context = AuthContext("user_approver", "tenant_001", "approver", "ACTIVE", "user_approver")
    app.dependency_overrides[get_auth_context] = lambda: context
    with TestClient(app, client=(f"approver-{uuid4().hex}", 50002)) as test_client:
        yield test_client
    app.dependency_overrides.clear()

