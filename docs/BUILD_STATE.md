# ROF12 build state

## Bootstrap status

- Fase 0: project scaffold, configuration, health endpoint, and reproducible local test setup.
- Fase 1: strict domain enums/contracts and mock-only model router.
- Fase 2: default-deny refund gate, tenant isolation, exact Decimal money handling, approvals, quarantine, and idempotency.
- Fase 3: PostgreSQL schema, composite tenant foreign keys, RLS, least-privilege roles, and immutable provenance storage.
- Fase 4: closed-claim JWT validation, database-resolved active memberships, frozen `AuthContext`, transaction-local RLS binding, and taint/provenance tracking.
- Fase 5: tenant-isolated document metadata/fragments, append-only grants, SHA-256 content identity, restricted filesystem storage, traversal protection, and tainted external-document ingestion.

All tests are local and use `MODEL_MODE=mock`. External model/API calls are intentionally unavailable in this bootstrap.

