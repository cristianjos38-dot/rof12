# ROF12 judge demo

## Local sequence

```bash
python3 -m pip install -e '.[dev]'
docker compose up -d postgres
make migrate
make seed
docker compose up -d rof12
python3 scripts/dev_token.py user_001
```

Use the generated token with:

```bash
curl http://localhost:8000/health
curl -H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: tenant_001" http://localhost:8000/tasks/context
```

## What to show

1. `/health` proves the service is up.
2. `/tasks/context` shows that `user_001` receives tenant and role from active database membership, not from the JWT.
3. The JWT payload contains no `tenant_id` or `roles` claim.
4. The PostgreSQL seed contains `order_1042` for `tenant_001` and `order_9999` for `tenant_002`.
5. Refund tests demonstrate allow, approval hold, capability denial, balance denial, duplicate denial, tenant mismatch and quarantine.
6. Document tests demonstrate taint-by-default and traversal-resistant tenant storage.

## Verification

```bash
make check
python3 -m pytest
python3 -m alembic upgrade head --sql >/tmp/rof12-schema.sql
```

The current repository has not claimed a live Docker result: if Docker is stopped, start it and rerun the sequence above before recording the final demo.

