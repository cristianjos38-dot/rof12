from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.api.dependencies import AuthContext, get_auth_context
from app.config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET
from app.main import app


def _token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "iat": 2_000_000_000, "exp": 2_000_000_900}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def test_tenant_b_cannot_read_tenant_a_task_audit():
    tenant_a = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
    tenant_b = AuthContext("user_002", "tenant_002", "operator", "ACTIVE", "user_002")
    app.dependency_overrides[get_auth_context] = lambda: tenant_a
    try:
        with TestClient(app, client=(f"tenant-a-{uuid4().hex}", 50101)) as client:
            created = client.post("/v1/tasks", headers={"Authorization": f"Bearer {_token('user_001')}", "X-Tenant-ID": "tenant_001"}, json={"task_type": "isolation", "payload": {"order_id": "order_1042"}})
            assert created.status_code == 200
            task_id = created.json()["task_id"]
        app.dependency_overrides[get_auth_context] = lambda: tenant_b
        with TestClient(app, client=(f"tenant-b-{uuid4().hex}", 50102)) as client:
            response = client.get(f"/v1/tasks/{task_id}/audit", headers={"Authorization": f"Bearer {_token('user_002')}", "X-Tenant-ID": "tenant_002"})
            assert response.status_code == 404
            assert response.json()["events"] if response.status_code == 200 else True
    finally:
        app.dependency_overrides.clear()


def test_tenant_b_cannot_fetch_tenant_a_task_or_cross_tenant_evaluate():
    tenant_a = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
    tenant_b = AuthContext("user_002", "tenant_002", "operator", "ACTIVE", "user_002")
    app.dependency_overrides[get_auth_context] = lambda: tenant_a
    try:
        with TestClient(app) as client:
            created = client.post("/v1/evaluate", headers={"Authorization": f"Bearer {_token('user_001')}", "X-Tenant-ID": "tenant_001"}, json={"task_type": "isolation", "payload": {"order_id": "order_1042"}})
            assert created.status_code == 200
            task_id = created.json()["task_id"]
        app.dependency_overrides[get_auth_context] = lambda: tenant_b
        with TestClient(app) as client:
            response = client.get(f"/v1/tasks/{task_id}", headers={"Authorization": f"Bearer {_token('user_002')}", "X-Tenant-ID": "tenant_002"})
            assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
