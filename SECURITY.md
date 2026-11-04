# ROF12 security posture

## Controls implemented

- Server authority: JWTs accept exactly `sub`, `iss`, `aud`, `exp` and `iat`; `tenant_id` and roles are never token claims.
- Active membership: tenant and role are selected from active database records, not from agent input.
- Default deny: refund decisions start denied and require explicit policy success.
- Strict schemas: Pydantic input models use `ConfigDict(extra="forbid")`.
- Exact money: Python uses `Decimal`; PostgreSQL uses `NUMERIC(12,2)` for money.
- Tenant isolation: composite foreign keys plus PostgreSQL RLS.
- Provenance: external document values start tainted and untrusted; only exact deterministic reconciliation can clear taint.
- Document isolation: tenant-specific filesystem roots, path traversal rejection, SHA-256 identity and restrictive local permissions.
- Secret hygiene: `.env`, private keys, secrets directories and caches are ignored; checked-in credentials are explicitly local development placeholders.
- Test isolation: tests run with `MODEL_MODE=mock` and do not call external APIs.

## Known limitations

- The live PostgreSQL/Docker demonstration has not been executed in this environment because the Docker daemon is unavailable.
- The `perception-worker` entry point and Compose isolation policy are implemented, but live container execution has not been validated because Docker is unavailable in this environment.
- The model router is hybrid: it supports the Meta-compatible live endpoint when explicitly enabled and degrades to deterministic, fail-closed behavior when credentials, network, or provider responses are unavailable.
- Development passwords in Compose/init are not production secrets and must be replaced by secret injection before deployment.

## Publication policy

Do not publish real `.env` files, API keys, JWT secrets, database dumps, customer data or private keys. Re-run the repository secret audit before every release.

