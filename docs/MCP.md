# ROF12 MCP bridge

ROF12 exposes two official MCP tools through `rof12.mcp_server`:

- `evaluate_proposal`: evaluates a structured proposal through the existing
  `SecurityGate` and returns a decision plus reasons; it never executes tools.
- `request_permit`: repeats the evaluation and returns an opaque permit only for
  `ALLOW`. The permit is not execution authority and does not bypass the Gate.

Local setup:

```bash
python -m pip install -e .
python scripts/mcp_smoke.py
python -m rof12.mcp_server
```

The MCP transport is stdio. Tenant and user values are process-owned server
context (`ROF12_MCP_TENANT_ID` and `ROF12_MCP_USER_ID` in the local harness),
never tool arguments supplied by the agent.

When `DATABASE_URL` and `ROF12_MCP_CAPABILITY_TOKEN` are configured, the
adapter resolves the capability and order under PostgreSQL RLS and runs
`VerityFlow` before the Gate. Without both values it reports
`evaluation_source=synthetic_fallback` and remains non-authoritative.
