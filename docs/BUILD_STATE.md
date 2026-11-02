# ROF12 build state

## Bootstrap status

- Fase 0: project scaffold, configuration, health endpoint, and reproducible local test setup.
- Fase 1: strict domain enums/contracts and mock-only model router.
- Fase 2: default-deny refund gate, tenant isolation, exact Decimal money handling, approvals, quarantine, and idempotency.

All tests are local and use `MODEL_MODE=mock`. External model/API calls are intentionally unavailable in this bootstrap.

