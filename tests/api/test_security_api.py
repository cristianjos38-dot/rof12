def headers():
    return {"Origin": "https://localhost", "X-Request-ID": "security-test", "X-CSRF-Token": "security-test"}


def test_security_admin_can_read_and_activate_kill_switch(security_client):
    assert security_client.get("/v1/security/status", headers=headers()).status_code == 200
    response = security_client.post("/v1/security/kill-switch", headers=headers())
    assert response.status_code == 200
    assert response.json()["kill_switch_active"] is True
    assert security_client.post("/v1/security/recovery", headers=headers()).json()["kill_switch_active"] is False


def test_security_endpoint_requires_csrf_and_origin(client):
    response = client.get("/v1/security/status")
    assert response.status_code in {401, 403}
    assert response.json()["code"] in {"HTTP_ERROR", "VALIDATION_ERROR"}

