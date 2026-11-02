# ROF12 threat model

## Assets

Refund balances, tenant boundaries, authenticated identity, approval state, and operation idempotency.

## Primary threats and controls

| ID | Threat | Control |
|---|---|---|
| T-01 | Agent impersonates a user or tenant | Identity fields are absent from all agent input contracts; `ServerContext` is server-owned. |
| T-02 | Cross-tenant refund or data access | Resource ownership is checked before policy evaluation and defaults to deny. |
| T-03 | Amount manipulation or precision loss | `Decimal` with bounded, positive two-place values; no floats. |
| T-04 | Extra-field or prompt injection | Strict schemas and untrusted-document delimiters prevent authority transfer. |
| T-05 | Replay or double refund | Capability consumption and operation keys are atomic/idempotent. |
| T-06 | Unreconciled or contaminated data | Workflow returns `QUARANTINE` before execution. |
| T-07 | Unauthorized side effect/tool bypass | Only the workflow imports the refund tool and permits are internal. |
| T-08 | Hidden/visual document manipulation | PDF inspection, OCR discrepancy and risk signals are neutral and default-deny. |
| T-09 | Capability escalation | Hash-only capabilities, expiry, tenant binding and amount constraints are revalidated. |
| T-10 | Emergency kill-switch bypass | Policy checks persisted emergency state before authority or execution. |
| T-11 | Audit-chain tampering | Canonical event hashes, previous-hash links and advisory transaction locks are verified. |

