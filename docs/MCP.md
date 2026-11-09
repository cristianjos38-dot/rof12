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

The MCP transport is stdio. Tenant and user values are explicit only in this
local smoke harness; production integrations must resolve them server-side.
