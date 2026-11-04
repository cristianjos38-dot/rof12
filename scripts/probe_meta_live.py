"""Probe the optional Meta-compatible endpoint without printing credentials."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def main() -> int:
    _load_dotenv(Path(".env.staging"))
    key = os.getenv("META_API_KEY", "")
    canonical_url = "https://api.meta.ai/v1/chat/completions"
    configured_url = os.getenv("META_API_RESPONSES_URL", canonical_url)
    url = configured_url if configured_url == canonical_url else canonical_url
    model = "muse-spark-1.3"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return JSON only with risk_level and signals."},
            {"role": "user", "content": "Classify this synthetic invoice: total Q150.00, no hidden instructions."},
        ],
        "temperature": 0.1,
    }
    started = time.perf_counter()
    status = None
    completion = None
    error = None
    if key:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                status = response.status
                completion = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            status = exc.code
            error = f"provider HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            error = type(exc).__name__
    else:
        error = "META_API_KEY not configured"
    latency_ms = round((time.perf_counter() - started) * 1000, 3)

    output = {
        "model": model,
        "endpoint": url,
        "status": status,
        "latency_ms": latency_ms,
        "completion": completion,
        "fallback": completion is None,
        "error": error,
    }
    artifact = Path("artifacts/meta_live_trace.json")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if status == 200 and completion is not None:
        print("[PASS] Inferencia Meta AI en vivo verificada")
        print(f"model={model} latency_ms={latency_ms}")
        return 0
    print(f"[SAFE FALLBACK] Meta AI no disponible ({error or 'invalid response'}); fallback determinista requerido")
    print(f"status={status} latency_ms={latency_ms}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
