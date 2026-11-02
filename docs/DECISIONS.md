# Architecture decisions

1. **Server context wins:** identity, tenant, and roles are passed separately from agent-authored requests.
2. **Default deny:** a policy decision is `DENY` until every required check is explicitly successful.
3. **Approval is a hold:** amounts above Q180.00 and at or below Q200.00 never execute immediately.
4. **In-memory phase-2 adapter:** the bootstrap keeps persistence deterministic and local; its interface can later be backed by a database.
5. **Mock model router:** `MODEL_MODE=mock` is the only supported test mode in this phase.

