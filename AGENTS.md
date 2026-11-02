# ROF12 agent instructions

- Treat `ServerContext` as the sole source of identity, tenant, and roles.
- Keep all monetary values as `Decimal`; never introduce `float` into domain code.
- Keep Pydantic input models strict with `ConfigDict(extra="forbid")`.
- Preserve default-deny behavior when adding policy dimensions.
- `app/tools/refund_service.py` may only be imported by `app/services/refund_workflow.py`.
- Tests must run with `MODEL_MODE=mock` and must not call external APIs.

## Persistent phase delivery rules

- Work exclusively on the authorized phase.
- Do not mix implementations from future phases.
- Run the corresponding tests before closing an advance.
- Review changes and detect sensitive files before publication.
- Do not create commits for incomplete functionality.
- When a validated milestone is complete, create a descriptive commit.
- Publish that commit immediately with `git publish`.
- Verify that the remote commit matches the local commit.
- Record changes and tests in the phase documentation.

Commit format:

```text
feat(phase-5): secure document ingestion
feat(phase-6): multimodal perception
feat(phase-7): capability manager
fix(phase-X): description of the correction
docs(phase-X): documentation of the advance
```

## Publication safety

- Never use `git push --force` or rewrite history.
- Never publish `.env` files, private keys or tokens.
- Never delete existing tags or change the repository owner.
- Never publish to the backup remote by mistake.
- Never mark a phase complete when required tests fail.
- Never publish experimental or incomplete changes.

