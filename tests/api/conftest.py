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
def security_client(monkeypatch):
    from app.api.security_dependencies import get_security_context
    from app.api.routes import security as security_routes

    state = {"active": False, "reason": ""}

    class Result:
        rowcount = 1

        def mappings(self):
            return self

        def first(self):
            return {"kill_switch_active": state["active"], "reason": state["reason"], "updated_at": None}

    class Connection:
        def execute(self, statement, params=None):
            sql = str(statement)
            if sql.startswith("SELECT kill_switch_active"):
                return Result()
            if "SET" in sql or "set_config" in sql:
                return Result()
            if "kill_switch_active = true" in sql:
                state["active"] = True
                state["reason"] = (params or {}).get("reason", "")
                return Result()
            if "kill_switch_active = false" in sql:
                state["active"] = False
                state["reason"] = ""
                return Result()
            return Result()

    class Engine:
        def begin(self):
            class Transaction:
                def __enter__(self):
                    return Connection()

                def __exit__(self, *_args):
                    return False

            return Transaction()

    monkeypatch.setattr(security_routes, "create_app_engine", lambda: Engine())
    monkeypatch.setattr(security_routes, "create_executor_engine", lambda: Engine())
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

