# ROF12 build state

CURRENT_PHASE: 8

## Bootstrap status

- Fase 0: project scaffold, configuration, health endpoint, and reproducible local test setup.
- Fase 1: strict domain enums/contracts and mock-only model router.
- Fase 2: default-deny refund gate, tenant isolation, exact Decimal money handling, approvals, quarantine, and idempotency.
- Fase 3: PostgreSQL schema, composite tenant foreign keys, RLS, least-privilege roles, and immutable provenance storage.
- Fase 4: closed-claim JWT validation, database-resolved active memberships, frozen `AuthContext`, transaction-local RLS binding, and taint/provenance tracking.
- Fase 5: chunked receipt, UUID4 artifact identities, extension/magic-byte checks, integrity validation, anti-tampering storage, quarantine, isolated perception worker configuration, and adversarial fixtures.
- Fase 6: deterministic PDF inspection, offline OCR interface, 160 DPI rendering, visual/embedded amount discrepancy detection, and neutral risk reports.
- Fase 7: SHA-256 capability storage, pure accumulated validation reasons, atomic one-time consumption, expiry and revocation.
- Fase 8: VerityFlow V1–V6 deterministic commercial checks with Decimal validation and row-lock SQL.

Fase 6–8 validation evidence: `37 passed`; all tests run locally with `MODEL_MODE=mock` and the VerityFlow suite supports `--disable-socket`.

All tests are local and use `MODEL_MODE=mock`. External model/API calls are intentionally unavailable in this bootstrap.

