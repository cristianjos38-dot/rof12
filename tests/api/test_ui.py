from datetime import datetime, timedelta, timezone

from app.api.routes.holds import hold_manager
from app.security.hold_manager import Hold


def test_dashboard_is_server_context_scoped_and_hardened(client):
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "tenant_001" in response.text
    assert "Content-Security-Policy" in response.headers
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "/ui/static/htmx.min.js" in response.text
    assert "https://cdn" not in response.text


def test_ui_partial_escapes_untrusted_artifact_text(client):
    from app.api.state import api_state

    with api_state.lock:
        api_state.artifacts[("tenant_001", "artifact-xss")] = {
            "artifact_id": "artifact-xss",
            "byte_size": 10,
            "original_filename": "<script>alert(1)</script>",
            "risk_report": None,
        }
    response = client.get("/ui/partials/artifacts")
    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert "<script>alert(1)</script>" not in response.text


def test_ui_holds_are_tenant_filtered(client):
    hold_manager.holds.clear()
    hold_manager.open(Hold("ui-own", "tenant_001", "user_001", datetime.now(timezone.utc) + timedelta(minutes=5)))
    hold_manager.open(Hold("ui-other", "tenant_002", "user_002", datetime.now(timezone.utc) + timedelta(minutes=5)))
    response = client.get("/ui/partials/holds")
    assert "ui-own" in response.text
    assert "ui-other" not in response.text
