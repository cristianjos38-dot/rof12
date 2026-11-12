# Changelog

## [1.1.0] - 2026-11-12

### Security and verification repair

- Closed the eight production-wiring fixes: fail-closed MCP evaluation, end-to-end kill switch, transactional refund execution, authenticated n8n integration, PostgreSQL-backed VerityFlow evaluation, algorithm-bound JWT configuration, chained audit verification, and supply-chain/API hardening.
- Closed the verification gaps with a PostgreSQL-backed corpus, a live kill-switch and capability-consumption race test in CI, and documented the structured-proposal taint boundary in [docs/MCP.md](docs/MCP.md) and the refunds API.

## [1.0.0] - 2026-11-09

### Added

- Runtime default-deny con contratos estrictos, provenance, VerityFlow y
  SecurityGate.
- PostgreSQL con RLS, capacidades atómicas, auditoría encadenada y API FastAPI.
- MCP server oficial, observabilidad OpenTelemetry y scaffold Azure.
- Corpus adversarial v2, propiedades Hypothesis y segundo dominio DevOps.

### Security

- Imagen Docker multi-stage no-root con digests fijados.
- Secret scanning/push protection, Dependabot, Gitleaks y SBOM CycloneDX.
