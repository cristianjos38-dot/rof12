from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import AuthContext
from app.api.security_dependencies import get_security_context
from app.main import app
from app.security.kill_switch import KillSwitch
from app.security.policy_engine import evaluate


pytestmark = pytest.mark.skipif(
    not os.getenv("ROF12_EXECUTOR_DB_URL"),
    reason="live PostgreSQL executor URL not configured",
)


def test_kill_switch_api_changes_live_gate_state():
    context = AuthContext("user_admin", "tenant_001", "security_admin", "ACTIVE", "user_admin")
    app.dependency_overrides[get_security_context] = lambda: context
    headers = {"Origin": "https://localhost", "X-Request-ID": "live-kill-switch"}
    try:
        with TestClient(app) as client:
            assert client.post("/v1/security/kill-switch", headers=headers).status_code == 200
            status = client.get("/v1/security/status", headers=headers)
            assert status.json()["kill_switch_active"] is True

            from sqlalchemy import create_engine

            engine = create_engine(os.environ["ROF12_EXECUTOR_DB_URL"])
            with engine.begin() as connection:
                state = KillSwitch().read(connection)
            result = evaluate(
                context,
                type("Request", (), {"tool_name": "refund_service"})(),
                type("Capability", (), {"valid": True, "reasons": ()})(),
                type("Provenance", (), {"is_tainted": False})(),
                type("Risk", (), {"risk_level": "LOW"})(),
                type("Verity", (), {"checks": {"V2": True, "V4": True, "V5": True}})(),
                state,
            )
            assert result.decision.value == "DENY"

            assert client.post("/v1/security/recovery", headers=headers).status_code == 200
            assert client.get("/v1/security/status", headers=headers).json()["kill_switch_active"] is False
    finally:
        app.dependency_overrides.clear()
