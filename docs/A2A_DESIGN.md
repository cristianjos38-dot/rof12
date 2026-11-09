# ROF12 A2A design

ROF12 is the policy enforcement boundary between an agent-to-agent message and
an operational tool. An A2A adapter accepts a signed, schema-validated
proposal, resolves the server-side `ServerContext`, attaches provenance, and
passes the proposal to `SecurityGate`. It returns a decision envelope and an
audit reference; it never forwards raw agent instructions to a tool.

For `ALLOW`, a single-use permit is bound to agent identity, tenant, tool,
argument hash, policy version, and expiry. `REQUIRE_APPROVAL` enters the human
hold workflow. `DENY` and `QUARANTINE` are terminal for that message. Every
transition is tenant-scoped and appended to the tamper-evident audit chain.

The transport may be MCP, HTTP, or a future A2A protocol binding. Transport
choice does not change policy, identity resolution, or execution authority.
