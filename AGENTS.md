# ROF12 agent instructions

- Treat `ServerContext` as the sole source of identity, tenant, and roles.
- Keep all monetary values as `Decimal`; never introduce `float` into domain code.
- Keep Pydantic input models strict with `ConfigDict(extra="forbid")`.
- Preserve default-deny behavior when adding policy dimensions.
- `app/tools/refund_service.py` may only be imported by `app/services/refund_workflow.py`.
- Tests must run with `MODEL_MODE=mock` and must not call external APIs.

