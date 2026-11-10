# Contributing to ROF12

1. Use Python 3.11 or 3.12 and install `pip install -e '.[dev]'`.
2. Work only on an authorized phase; do not modify frozen domain contracts.
3. Run `MODEL_MODE=mock make check` before every commit.
4. Run `make sbom` and review sensitive-file changes before publication.
5. Use descriptive phase commits and never commit `.env`, credentials, dumps,
   generated audio/video, or private keys.

Security-sensitive changes require tests for default-deny behavior, tenant
isolation, Decimal monetary handling, idempotency, and audit-chain integrity.
