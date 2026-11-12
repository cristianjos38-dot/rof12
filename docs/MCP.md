# ROF12 MCP bridge

ROF12 exposes three official MCP tools through `rof12.mcp_server`:

- `evaluate_proposal`: evaluates a structured proposal through the existing
  `SecurityGate` and returns a decision plus reasons; it never executes tools.
- `request_permit`: repeats the evaluation and returns an opaque permit only for
  `ALLOW`. The permit is not execution authority and does not bypass the Gate.
- `execute_refund`: revalidates and executes the refund inside the server-owned
  PostgreSQL transaction; it never serializes a permit to MCP.

Local setup:

```bash
python -m pip install -e .
python scripts/mcp_smoke.py
python -m rof12.mcp_server
```

The MCP transport is stdio. Tenant and user values are process-owned server
context (`ROF12_MCP_TENANT_ID` and `ROF12_MCP_USER_ID` in the local harness),
never tool arguments supplied by the agent.

When `DATABASE_URL`, `ROF12_MCP_CAPABILITY_TOKEN`, `ROF12_MCP_TENANT_ID`, and
`ROF12_MCP_USER_ID` are configured, the adapter resolves the capability and
order under PostgreSQL RLS and runs `VerityFlow` before the Gate. Without the
full configuration it returns `MCP_NOT_CONFIGURED`; database failures return
`MCP_DATABASE_ERROR`. There is no synthetic evaluation fallback.

## Limitations

Structured MCP proposals do not carry a document on which provenance analysis
can operate. Therefore the structured path uses the documented defaults
`is_tainted=False` and `risk_level=LOW`; its boundary is the server-verified
identity, capability, order state, VerityFlow checks, idempotency and kill
switch. An `order_id` or `amount` copied from a poisoned document is not
detected by taint tracking on this path; route documents through the ingestion
and perception pipeline when provenance analysis is required.
