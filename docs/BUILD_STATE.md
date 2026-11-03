# ROF12 build state

CURRENT_PHASE: 18
CURRENT_SESSION: 18.3
LAST_VALIDATED: "Eficacia adversarial certificada al 100% en vivo contra Supabase. Benchmark generado en demo_benchmark.json. Auditoría criptográfica validada. Entorno completamente listo para grabación."
NEXT_ACTION: "Grabación de video técnico de demostración (3 minutos)."

## Posicionamiento del núcleo

ROF12 es un Runtime de Ejecución Segura y Freno Universal para Agentes de IA,
agnóstico a la industria. Los reembolsos son el primer caso demostrable; las
Capacidades atómicas, Taint Tracking, VerityFlow, Policy Engine Default-Deny,
Security Gate y Audit Chain son controles universales aplicables también a
DevOps, Finanzas, Legal y APIs operativas. La Fase 17 está validada en vivo
contra Supabase y el endpoint público ngrok configurado para la demostración.

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
- Fase 14: server-rendered control panel with local HTMX, strict Jinja autoescape, tenant-scoped service-backed views and browser security headers.
- Fase 15: adversarial security laboratory, threat-ID coverage, atomicity stress harness and resilience checks.
- Fase 16: clean-clone Docker bootstrap, seven-fixture Baseline vs Protected replay, PostgreSQL result recording and delivery documentation.

Fase 15 validation evidence: adversarial suite `13 passed`; full suite `79 passed, 1 skipped`; Ruff and Pyright report zero errors; `pip-audit .` reports no known vulnerabilities under Python 3.11. The skipped resilience check requires a live PostgreSQL Docker environment.
Fase 16 validation evidence: Docker Compose built and started, Alembic reached head, the seven-fixture replay was persisted/read from PostgreSQL, `/health/ready` returned `database=ok`, and the live PostgreSQL reconnection test passed. The clean-clone README flow is reproducible with Python 3.11+.
Fase 18.1 validation evidence: the formatted seven-fixture replay ran against Supabase, `scripts/prep_demo.sh` seeded idempotently, `/health/ready` reported `database=ok`, and the authenticated dashboard responded at `/ui/`. Docker was unavailable in the current host session.
Fase 18.3 live benchmark evidence: Supabase seed completed idempotently, `/health/ready` returned `database=ok`, and `demo_benchmark.json` recorded 14 rows. Protected evaluation produced T-01 `ALLOW` and T-02–T-07 `QUARANTINE`: 6/6 hostile fixtures blocked (100% detection), 0 false positives, and 3.639 ms mean Protected latency. The Supabase audit chain contained 20 events, grouped decisions `ALLOW=5`, `DENY=2`, `QUARANTINE=13`, with SHA-256 links verified end-to-end. Full suite: `83 passed, 1 skipped`; the skipped resilience check requires live Docker PostgreSQL.

All tests are local and use `MODEL_MODE=mock`. External model/API calls are intentionally unavailable in this bootstrap. The supported runtime is Python 3.11+.

