# ROF12 — Decision-Level Authorization Runtime for AI Agents

[![CI](https://github.com/cristianjos38-dot/rof12/actions/workflows/ci.yml/badge.svg)](https://github.com/cristianjos38-dot/rof12/actions/workflows/ci.yml) [![Coverage](https://img.shields.io/badge/coverage-77%25-blue)](docs/BENCHMARKS.md) [![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE) [![Version](https://img.shields.io/badge/version-1.0.0-blue)](pyproject.toml)

ROF12 is a decision-level authorization runtime for AI agents: the agent proposes, the runtime verifies, and no consequential action executes without a permit the agent cannot mint.

## What it is

- A server-authoritative decision boundary between an agent proposal and a side-effecting tool.
- A deterministic verification and policy path for identity, tenant ownership, provenance, amount, capability, state, and idempotency.
- A PostgreSQL-backed runtime with row-level tenant isolation, atomic capabilities, human approval holds, an emergency kill switch, and a chained audit log.

## What it is not

- It is not an agent framework or an autonomous executor.
- It is not a replacement for Entra, Purview, Defender, or a provider identity system.
- It is not a production-proven product; the repository contains local and CI evidence only.
- It does not let a model make the final decision. Model output is a signal; deterministic policy is the decider, and failure falls back to deny or quarantine.

## How it works

```text
Agent or MCP client
        |
        v
ServerContext + AuthContext
        |
Provenance -> VerityFlow -> Policy Engine -> SecurityGate
      |              |              |              |
      +--------------+--------------+--------------+
                                      |
                         internal Permit -> tool
                                      |
                         Audit Chain + PostgreSQL RLS
```

`app/provenance.py` marks external values as tainted and permits deterministic reconciliation only. `app/verification/verityflow.py` performs the six commercial checks without calling a model. `app/security/policy_engine.py` combines identity, action, resource, authority, constraints, taint, kill-switch, and approval dimensions using default-deny logic. `app/security/security_gate.py` is the final boundary and is the only component that can mint the internal permit. The standalone core is in `rof12/core.py`.

## Invariants

- Default-deny is the initial and failure state: `app/security/policy_engine.py`.
- Monetary values use bounded `Decimal` in Python and `NUMERIC(12,2)` in PostgreSQL; domain code does not use floats: `app/domain/contracts.py`, `app/persistence/tables.py`.
- JWT validation accepts a closed claim set. Tenant, role, membership, and capability scope come from server-side stores: `app/api/authentication.py`, `app/api/dependencies.py`.
- Tenant-aware tables use PostgreSQL RLS with `app.tenant_id` and composite tenant foreign keys: `migrations/`, `docs/SUPABASE_STAGING.md`.
- Permits are non-serializable and can only be minted by `SecurityGate` after `ALLOW`: `app/security/security_gate.py`.
- Duplicate submission does not execute twice: capability consumption and refund operation handling are conditional and idempotent: `app/security/capability_manager.py`, `app/services/refund_workflow.py`.
- `app/tools/refund_service.py` is imported only by `app/services/refund_workflow.py`.

## Threat model

| Vector | Control |
|---|---|
| T-01: agent impersonates a user or tenant | Server-owned identity; agent contracts contain no identity authority. |
| T-02: cross-tenant access | Ownership checks and PostgreSQL RLS default to no rows. |
| T-03: amount or precision manipulation | Positive, bounded `Decimal` values and `NUMERIC(12,2)`. |
| T-04: extra fields or prompt injection | Strict schemas, tainted provenance, and default-deny policy evaluation. |
| T-05: replay or double refund | Atomic capability consumption and operation idempotency. |
| T-06: contaminated data | Unreconciled values terminate in `QUARANTINE`. |
| T-07: tool bypass | Internal permits and a single workflow import boundary. |
| T-08: hidden document manipulation | PDF inspection, OCR comparison, and neutral risk signals. |
| T-09: capability escalation | Hash-only tokens, expiry, tenant binding, user binding, and amount limits. |
| T-10: emergency bypass | Kill-switch state is checked before authority and execution. |
| T-11: audit tampering | Canonical event hashes, previous-hash links, and transaction locks. |

See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for the detailed assets and controls.

## Evaluation

The evaluation corpus is synthetic and deterministic:

- The v2 adversarial corpus contains 25 cases: 7 original vectors and 18 additional vectors in [attacks/v2_manifest.json](attacks/v2_manifest.json).
- The legitimate corpus contains 20 clean-document records. The measured lab result is `0/20` false positives for the deterministic fixture classifier; it is not a production accuracy claim.
- Hypothesis tests cover Decimal precision, capability expiry, and audit-chain tampering.
- A second domain, DevOps deployment approval, reuses the same Gate and has one allowed case plus four denied cases.
- The latest local pure Gate benchmark measured `0.0052 ms` average, `0.0051 ms` p50, and `0.0053 ms` p95 over 1,000 in-memory calls. The protected document replay artifact measured `3.639 ms` average over seven persisted protected rows. These are different methods and are not interchangeable.

Reproduce the corpus and property results with:

```bash
MODEL_MODE=mock python3.11 -m pytest tests/test_evaluation_v2.py tests/test_properties.py tests/test_devops_domain.py -q
python3.11 scripts/run_attack_round.py
python3.11 scripts/bench_gate.py
```

The benchmark method and provenance are recorded in [docs/BENCHMARKS.md](docs/BENCHMARKS.md); evaluation methodology is in [docs/EVALUATION.md](docs/EVALUATION.md).

## Quickstart: standalone, no Docker

The standalone example uses only synthetic in-memory state and requires no database key or model API:

```bash
python3.11 examples/quickstart.py
# $45.00: ALLOW
# $1850.00: DENY
```

## Full stack: PostgreSQL 16 and FastAPI

Run the documented local stack:

```bash
cp .env.example .env
mkdir -p secrets
printf 'lab-password\n' > secrets/db_password.txt
python3.11 -m pip install -e '.[dev]'
docker compose up -d --build
docker compose exec api alembic upgrade head
make seed
curl -fsS http://127.0.0.1:8000/health/ready
```

The API has a local development fallback when `DATABASE_URL` is absent. The protected evaluation endpoint is `POST /v1/evaluate`; its body contains the task type and payload, while the authenticated context is resolved by the server. With a seeded local database, a laboratory request can be sent with a generated token:

```bash
export DEMO_JWT="$(python3.11 scripts/dev_token.py user_001)"
curl -fsS -X POST http://127.0.0.1:8000/v1/evaluate \
  -H "Authorization: Bearer $DEMO_JWT" \
  -H "X-Tenant-ID: tenant_001" \
  -H "Content-Type: application/json" \
  -d '{"task_type":"refund_review","payload":{"order_id":"order_1042"}}'
```

The local token contains only `sub`, `iss`, `aud`, `exp`, and `iat`. The API requires PostgreSQL membership resolution before a protected request is accepted.

## MCP bridge

`rof12/mcp_server.py` exposes two stdio MCP tools:

- `evaluate_proposal` evaluates a proposal and returns a decision without executing a tool.
- `request_permit` repeats the evaluation and returns an opaque permit only for `ALLOW`; the permit is not execution authority.

Tenant and user values are process-owned server context, never agent-supplied tool arguments. When `DATABASE_URL` and `ROF12_MCP_CAPABILITY_TOKEN` are configured, the bridge loads capability and order state under PostgreSQL RLS, runs real VerityFlow, and then invokes the SecurityGate. Without both values it reports `synthetic_fallback` and remains non-authoritative.

Run the local smoke test and inspect the client example:

```bash
MODEL_MODE=mock python3.11 scripts/mcp_smoke.py
sed -n '1,120p' examples/mcp_client.py
```

See [docs/MCP.md](docs/MCP.md) and [docs/IDENTITY.md](docs/IDENTITY.md).

## Optional model adapters

The optional adapters expose `muse-spark-1.3` for risk signals, `sam-3.1` for evidence boxes and masks, and `muse-wonder-1.0` for plans and proposals. Model output is never an execution decision. Missing credentials, non-live mode, network failure, or malformed responses use deterministic local fallback behavior.

```bash
export MODEL_MODE=live
export META_API_KEY='<injected-by-secret-manager>'
export META_API_BASE_URL='https://api.meta.ai/v1'
export META_API_RESPONSES_URL='https://api.meta.ai/v1/chat/completions'
```

The macOS voice terminal is an experimental adapter and is not required by the core runtime; see [contrib/README.md](contrib/README.md).

## Deployment

The Docker image uses a multi-stage build, a pinned base-image digest, and non-root UID 10001. Operations guidance, migrations, backup, restore, and SBOM generation are in [docs/OPERATIONS.md](docs/OPERATIONS.md).

An Azure Container Apps scaffold is available in [azure.yaml](azure.yaml) and [azure/main.bicep](azure/main.bicep). The documented command is `azd up`, but it was not tested because this environment has no Azure CLI or authenticated subscription. See [docs/DEPLOY_AZURE.md](docs/DEPLOY_AZURE.md).

Supabase staging configuration and its current verification limits are documented in [docs/SUPABASE_STAGING.md](docs/SUPABASE_STAGING.md). The live audit-event count is not certified; the document records the historical count of four events and the connection failure observed during the final audit.

## Security

- `.env`, staging files, secrets, private keys, caches, generated media, and the local SBOM are ignored by Git.
- No credentials, connection strings with passwords, or provider tokens belong in the repository.
- The SBOM is regenerated with `make sbom` and attached to the [v1.0.0 GitHub release](https://github.com/cristianjos38-dot/rof12/releases/tag/v1.0.0); it is not tracked in `master`.
- Report suspected vulnerabilities privately using the process in [SECURITY.md](SECURITY.md).

## Contributing and release

Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing the repository. The release history is in [CHANGELOG.md](CHANGELOG.md). The package metadata is `rof12==1.0.0`, but PyPI publication is pending; installation is currently from Git or from a locally built distribution. See [docs/RELEASING.md](docs/RELEASING.md) for the authorized publication commands.

The full historical phase inventory is preserved in [docs/HISTORY.md](docs/HISTORY.md). The independent demo harness is documented in [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).
