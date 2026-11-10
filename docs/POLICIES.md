# Policy files

The repository intentionally contains two policy documents with different
audiences:

- `policy/policy.json` is the canonical runtime policy consumed by the
  standalone ROF12 defensive engine.
- `rof12-demo/policy/policy.json` belongs to the isolated presentation harness;
  it keeps demo-only thresholds and narration fixtures separate from runtime
  enforcement.

Neither file grants authority by itself. All operational proposals still pass
through the server-owned context and `SecurityGate`.
