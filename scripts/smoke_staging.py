"""Small, secret-safe smoke test for a deployed ROF12 staging API."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _request(base_url: str, path: str, *, token: str = "", body: dict | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-Tenant-ID"] = os.environ.get("STAGING_TENANT_ID", "")
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = Request(f"{base_url}{path}", headers=headers, data=data, method="POST" if body else "GET")
    try:
        with urlopen(request, timeout=float(os.getenv("STAGING_SMOKE_TIMEOUT", "10"))) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return exc.code, {}
    except URLError as exc:
        raise RuntimeError(f"staging endpoint unavailable: {exc.reason}") from exc


def main() -> int:
    base_url = os.getenv("STAGING_BASE_URL", "").rstrip("/")
    if not base_url:
        print("STAGING_BASE_URL is required", file=sys.stderr)
        return 2
    status, payload = _request(base_url, "/health/ready")
    if status != 200 or payload.get("status") != "ready" or payload.get("database") != "ok":
        print(f"staging readiness failed: HTTP {status}", file=sys.stderr)
        return 1
    print("staging readiness: ok")

    token = os.getenv("STAGING_JWT", "")
    tenant_id = os.getenv("STAGING_TENANT_ID", "")
    if not token or not tenant_id:
        print("authenticated smoke skipped: STAGING_JWT/STAGING_TENANT_ID not configured")
        return 0

    status, _ = _request(base_url, "/v1/tasks", token=token, body={"task_type": "staging_smoke", "payload": {"order_id": "order_1042"}})
    if status not in {200, 201, 202}:
        print(f"authenticated benign flow failed: HTTP {status}", file=sys.stderr)
        return 1
    status, payload = _request(base_url, "/v1/tasks", token=token, body={"task_type": "staging_smoke", "payload": {"order_id": "order_1042"}, "tenant_id": tenant_id})
    if status != 422 or payload.get("code") not in {"VALIDATION_ERROR", "validation_error"}:
        print(f"authority rejection failed: HTTP {status}", file=sys.stderr)
        return 1
    print("authenticated benign flow: ok; agent-supplied tenant rejected: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
