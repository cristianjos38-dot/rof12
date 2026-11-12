from fastapi.testclient import TestClient

from app.main import app


def test_n8n_requires_authentication():
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        response = test_client.post(
            "/v1/n8n/inspect-email",
            json={"sender": "synthetic@example.invalid", "subject": "invoice", "document_text": "hello"},
        )
    assert response.status_code == 401


def test_n8n_uses_server_context_and_does_not_return_permit(client):
    response = client.post(
        "/v1/n8n/inspect-email",
        json={
            "sender": "synthetic@example.invalid",
            "subject": "invoice",
            "document_text": "synthetic invoice for order_1042",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "permit_token" not in body
    assert body["evaluation_source"] in {"heuristic", "postgres_verityflow"}
    if body["evaluation_source"] == "postgres_verityflow":
        import os

        from sqlalchemy import create_engine, text

        with create_engine(os.environ["DATABASE_OWNER_URL"]).begin() as connection:
            persisted = connection.execute(
                text("SELECT 1 FROM rof12.audit_events WHERE tenant_id = 'tenant_001' AND event_type = 'N8N_EMAIL_INSPECTION' LIMIT 1")
            ).first()
        assert persisted is not None
    else:
        assert ("tenant_001", "n8n-email-inspection") in __import__("app.api.state", fromlist=["api_state"]).api_state.audit


def test_n8n_body_cannot_supply_tenant(client):
    response = client.post(
        "/v1/n8n/inspect-email",
        json={
            "sender": "synthetic@example.invalid",
            "subject": "invoice",
            "document_text": "hello",
            "tenant_id": "tenant_002",
        },
    )
    assert response.status_code == 422
