# ROF12 build state

CURRENT_PHASE: 13

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
- Fase 9: pure default-deny Policy Engine with kill-switch, identity, action, resource, authority, constraint and taint dimensions.
- Fase 10: hold state machine, authorized revalidation, kill switch, and cryptographically chained audit logger.
- Fase 11: internal non-serializable execution permits, immutable tool registry, transactional refund execution and outbox events.
- Fase 12: Meta multi-mode router, preventive budget guard, read-only orchestrator, prompt delimiters, SAM parser and adversarial mock mode.
- Fase 13: protected FastAPI v1 routes, request IDs, sanitized structured logging, uniform JSON errors and security administration endpoints.

Fase 6–8 validation evidence: `37 passed`; Fase 9–11 adds deterministic policy, hold, audit and gate suites; Fase 12 raises the full local suite to `53 passed`. All tests run without LLM calls; adversarial mode is intentionally synthetic.

All tests are local and use `MODEL_MODE=mock`. External model/API calls are intentionally unavailable in this bootstrap.

