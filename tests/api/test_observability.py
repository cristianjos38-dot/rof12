def test_request_id_is_generated_and_propagated(client):
    response = client.get("/v1/tasks/missing")
    assert response.status_code == 404
    assert response.headers.get("X-Request-ID")
    assert response.json()["code"] == "HTTP_ERROR"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_request_id_is_preserved(client):
    response = client.get("/health", headers={"X-Request-ID": "known-request"})
    assert response.headers["X-Request-ID"] == "known-request"


def test_rate_limit_is_json(client):
    responses = [client.post("/v1/tasks", json={"task_type": "rate", "payload": {}}) for _ in range(35)]
    limited = [item for item in responses if item.status_code == 429]
    assert limited
    assert limited[-1].json()["code"] == "RATE_LIMITED"

