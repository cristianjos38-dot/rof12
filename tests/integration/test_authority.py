from dataclasses import FrozenInstanceError

import pytest

from app.api.dependencies import AuthContext, RLS_SET_LOCAL_SQL


def test_auth_context_is_frozen_and_contains_server_resolved_fields():
    context = AuthContext("user_001", "tenant_001", "operator", "ACTIVE", "user_001")
    assert context.token_sub == context.user_id
    with pytest.raises(FrozenInstanceError):
        context.tenant_id = "tenant_002"


def test_rls_context_is_transaction_local_and_parameterized():
    assert RLS_SET_LOCAL_SQL == "SET LOCAL app.tenant_id = :tenant_id"


def test_authority_resolution_is_tenant_and_status_scoped():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / "app" / "api" / "dependencies.py").read_text(encoding="utf-8")
    assert "m.tenant_id = :tenant_id" in source
    assert "m.user_id = :user_id" in source
    assert "m.status = 'ACTIVE'" in source
    assert "u.status = 'ACTIVE'" in source

