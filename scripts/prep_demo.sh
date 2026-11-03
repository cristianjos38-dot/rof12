#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_OWNER_URL:?DATABASE_OWNER_URL is required for demo persistence}"
DEMO_BASE_URL="${DEMO_BASE_URL:-http://127.0.0.1:8000}"
DEMO_TENANT_ID="${DEMO_TENANT_ID:-tenant_001}"
DEMO_JWT="${DEMO_JWT:-}"

if [[ "$DEMO_BASE_URL" == http://127.0.0.1:8000 || "$DEMO_BASE_URL" == http://localhost:8000 ]]; then
  : "${DATABASE_URL:?DATABASE_URL is required when starting the local API}"
  if ! curl -fsS "$DEMO_BASE_URL/health/ready" >/dev/null 2>&1; then
    nohup env MODEL_MODE=mock DATABASE_PREPARE_THRESHOLD="${DATABASE_PREPARE_THRESHOLD:-none}" DATABASE_URL="$DATABASE_URL" \
      python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >/tmp/rof12-demo-api.log 2>&1 &
    api_pid=$!
    echo "api_pid=$api_pid"
    for _ in {1..15}; do
      curl -fsS "$DEMO_BASE_URL/health/ready" >/dev/null 2>&1 && break
      sleep 1
    done
  fi
fi

DATABASE_OWNER_URL="$DATABASE_OWNER_URL" python3.11 scripts/seed.py
printf 'readiness: '
curl -fsS "$DEMO_BASE_URL/health/ready"
printf '\n'

if [[ -n "$DEMO_JWT" ]]; then
  curl -fsS -H "Authorization: Bearer $DEMO_JWT" -H "X-Tenant-ID: $DEMO_TENANT_ID" "$DEMO_BASE_URL/ui/" >/dev/null
  echo "ui: available at $DEMO_BASE_URL/ui/"
else
  echo "ui: protected; set DEMO_JWT to verify the authenticated dashboard"
fi

DATABASE_OWNER_URL="$DATABASE_OWNER_URL" python3.11 demo/run_demonstration.py
