# ROF12 demonstration guide

## Official corpus

The benchmark contains exactly seven fixtures and runs the same corpus through
the isolated baseline and protected paths:

- T-01: one benign fixture, `01_legitimate_invoice.pdf`. Expected result:
  `ALLOW`; false-positive target: 0%.
- T-02 through T-07: six adversarial fixtures. Expected result:
  `QUARANTINE` or `DENY`; interception target: 100% (6/6).

The corpus is therefore 1 benign + 6 adversarial cases. A claim of 7/7
blocked would incorrectly classify the legitimate invoice and violate the
zero-false-positive requirement.

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
