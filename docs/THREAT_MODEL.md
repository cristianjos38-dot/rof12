# ROF12 threat model

## Assets

Refund balances, tenant boundaries, authenticated identity, approval state, and operation idempotency.

## Primary threats and controls

| Threat | Control |
|---|---|
| Agent impersonates a user or tenant | Identity fields are absent from all agent input contracts; `ServerContext` is server-owned. |
| Cross-tenant refund | Resource ownership is checked before policy evaluation and defaults to deny. |
| Amount manipulation/precision loss | `Decimal` with bounded, positive two-place values; no floats. |
| Extra-field prompt/schema injection | Every input model forbids extras. |
| Replay/double refund | Operation key is stored and repeated requests are denied. |
| Unreconciled or contaminated data | Workflow returns `QUARANTINE` before execution. |
| Unauthorized side effect | Only the workflow imports the refund tool. |

