# Project history

The README describes the current v1.0.0 mechanism. This file preserves the
internal phase inventory that led to the release without treating phase labels
as product capabilities or production certification.

| Phase | Historical scope |
|---|---|
| F0 | Repository scaffold, configuration, health endpoint, and local tests. |
| F1 | Frozen domain contracts, strict Pydantic inputs, and mock model routing. |
| F2 | Deterministic refund Gate, limits, approval, quarantine, and idempotency. |
| F3 | PostgreSQL persistence, Alembic migrations, RLS, composite foreign keys, roles, and production hardening. |
| F4 | JWT verification, immutable authentication context, memberships, provenance, and taint tracking. |
| F5 | Isolated document ingestion, SHA-256 storage, validation, and quarantine. |
| F6 | PDF inspection, OCR interfaces, visual comparison, and neutral risk reporting. |
| F7 | Hash-only capabilities, atomic consumption, expiry, and revocation. |
| F8 | Deterministic VerityFlow checks V1–V6 using Decimal values. |
| F9 | Pure default-deny Policy Engine with taint-aware decisions. |
| F10 | Human approval holds, emergency kill switch, and cryptographic audit chain. |
| F11 | SecurityGate integration, internal permits, and transactional execution. |
| F12 | Optional model router, read-only orchestration, prompts, and budget guard. |
| F13 | FastAPI endpoints, structured errors, rate limiting, and observability. |
| F14 | Server-rendered Jinja2 dashboard with local HTMX and tenant isolation. |
| F15 | Adversarial laboratory, threat coverage, and reproducible quality gates. |
| F16 | Baseline/protected replay harness and Docker reproducibility work. |
| F17 | Staging deployment scaffolding and documented Supabase, Azure, and perimeter concerns. |
| F18 | Demonstration harness, RLS evidence, optional model probes, voice adapter, and release preparation. |

The released hardening scope is organized in the repository as production
mechanisms, tests, and operational documentation rather than as a claim that
every historical phase is a deployed production service.
