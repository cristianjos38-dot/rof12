from datetime import UTC, datetime, timedelta

from app.api.routes.holds import hold_manager
from app.security.hold_manager import Hold


def test_hold_query_and_resolution(approver_client):
    hold_manager.open(Hold("api-hold", "tenant_001", "user_001", datetime.now(UTC) + timedelta(minutes=5)))
    assert approver_client.get("/v1/holds").status_code == 200
    assert approver_client.get("/v1/holds/api-hold").json()["hold_id"] == "api-hold"
    response = approver_client.post("/v1/holds/api-hold/resolve", json={"approve": False})
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_hold_resolution_rejects_extra_identity(client):
    response = client.post("/v1/holds/missing/resolve", json={"approve": True, "tenant_id": "tenant_002"})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"

