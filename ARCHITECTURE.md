# ROF12 architecture

ROF12 is a server-authoritative runtime for AI agents. Agent-authored requests contain intent and business payload only; identity, tenant and roles come from authenticated server context.

```text
JWT (sub only)
      |
      v
FastAPI authentication -> active DB membership -> frozen AuthContext
      |                                  |
      |                                  +--> transaction-local app.tenant_id (RLS)
      v
strict contracts -> default-deny refund workflow -> side-effect tool
      |
      +--> document ingestor -> tenant filesystem boundary + SHA-256
      +--> provenance tracker -> taint by default / exact reconciliation
      +--> PostgreSQL audit and operational tables
```

## Runtime boundaries

- `app/api/authentication.py` validates the JWT signature, issuer, audience, expiry and exact claim set.
- `app/api/dependencies.py` resolves `users` and active `memberships` in PostgreSQL, then binds RLS context.
- `app/domain/` contains frozen contracts and enums.
- `app/services/refund_workflow.py` is the only module allowed to import the refund side-effect tool.
- `app/documents.py` validates filenames, computes content identity and writes only inside a tenant-specific directory.
- Alembic migrations define composite tenant foreign keys and RLS policies.

## Persistence

All tenant-aware tables use `tenant_id`, RLS and `current_setting('app.tenant_id', true)`. Child records reference parents with `(tenant_id, foreign_id)` composite keys. PostgreSQL roles separate migrations, API access, executor writes and audit writes.

The current baseline uses a local mock model router for deterministic tests. A `perception-worker` is not implemented in this repository.

