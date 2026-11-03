# ROF12 security audit

Audit date: 2026-11-03

## Scope and result

The audit covered the public Git history, configuration templates, standalone
demo, application tests, Supabase staging metadata, and dependency inventory.
No private key, `.env` file, staging secret, or token file is tracked. The
public template contains placeholders only. `.env.staging` remains ignored.

## Seven pillars

| Pillar | Evidence | Result |
|---|---|---|
| 1. Audit integrity | Recomputed `prev_hash` and SHA-256 event hash for 76 Supabase events in `chain_sequence` order. | PASS |
| 2. Meta inference | `MetaClient` uses `META_API_RESPONSES_URL`, supports all three model names, and falls back on missing key, timeout, transport error, or invalid response. Live execution in this environment returned no usable provider response; fallback was observed: Spark `CRITICAL`, SAM box/mask, Wonder proposal. | PASS with fallback evidence; provider response contract still requires live vendor confirmation |
| 3. Permit binding | HMAC covers the canonical permit containing agent, tenant, tool, `args_hash`, proposal hash, issue time and expiry. Added tests reject changed agent and tenant. | PASS |
| 4. Atomic consumption | `CapabilityManager.consume()` uses conditional `UPDATE ... WHERE status='ACTIVE' AND expires_at > :now RETURNING capability_id`; concurrency test and full suite pass. | PASS |
| 5. Human approval | `HoldManager` restricts resolution to `approver`, `admin`, or `security_admin`; revalidates before approval. Hold state now records `approver_id` and justification. | PASS |
| 6. Tenant isolation | 15 tenant-aware tables have RLS enabled and 15 policies use `current_setting('app.tenant_id', true)`. Live Supabase probe executed as `rof12_app` with session tenant `tenant_002`; querying `tenant_001` returned 0 rows. | PASS |
| 7. Dependencies | `pip-audit` reported no known vulnerabilities. It also reported the local editable project `rof12` is not a PyPI package, which is expected and not a third-party vulnerability. | PASS |

## Verification commands

- Demo tests: 13 passed, including agent/tenant permit binding.
- Core suite: 85 passed, 1 skipped; the skip requires live Docker PostgreSQL.
- Standalone demo: `python3.11 rof12-demo/run_demo.py all --fast` passed.
- Tamper test: detected modified JSONL hash chain.
- Supabase audit chain: 76/76 links and hashes valid.
- API isolation test: `tests/security/test_rls_isolation.py` passes for two
  server-resolved tenant contexts; Tenant B receives 404 for Tenant A task and
  audit resources. The direct PostgreSQL `rof12_app` probe now also passes.

## Recording runner

Use `python3.11 demo/run_video_demo.py --interactive` for the seven-case
screen recording. It pauses 1.5 seconds by default, prints the model sources,
Gate decision, SHA-256, and whether the persisted replay can confirm the hash.

## Secret hygiene notes

Historical scans are intentionally interpreted by file classification, not raw
keyword counts: code and documentation necessarily contain names such as
`META_API_KEY`, `Bearer`, and `JWT_SECRET`. The actual credential-bearing
`.env.staging` is ignored and absent from `git ls-files`. Any key pasted into a
chat or terminal must be rotated before production use.
