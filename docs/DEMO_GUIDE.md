# ROF12 demonstration guide

## Official corpus

The benchmark contains exactly seven fixtures and runs the same corpus through
the isolated baseline and protected paths:

- T-01: a benign fixture, `01_legitimate_invoice.pdf`, verified as a
  non-hostile control.
- T-02 through T-07: adversarial fixtures evaluated by the defensive gate.

The signed laboratory report records 7 of 7 synthetic vectors neutralized
(2 `QUARANTINE`, 5 `DENY`) and 0 false positives.

## Rehearsal

```bash
set -a && source .env.staging && set +a
make prep-demo
curl -fsS http://127.0.0.1:8000/health/ready
python3.11 demo/run_demonstration.py
make check
```

The protected replay must report T-01 as `[PROTECTED: ALLOW]` and T-02–T-07
as `[PROTECTED: BLOCKED]`. Results and audit events are persisted transactionally
in Supabase; the audit chain is verified with SHA-256 links.
