# ROF12 evaluation methodology

The v2 adversarial corpus contains 7 original vectors plus 18 additional
synthetic vectors (25 total). The expected decision and reason for every new
vector are in `attacks/v2_manifest.json`. The legitimate corpus contains 20
synthetic clean-document records; each is sent through the canonical
application `SecurityGate` with clean provenance and all VerityFlow dimensions
true. Its measured false-positive rate is `0/20 = 0%`; this is a single-machine
laboratory result, not a production accuracy claim or a held-out evaluation.
The tests require the CI PostgreSQL service and are intentionally skipped on a
developer machine without `DATABASE_OWNER_URL` and `ROF12_EXECUTOR_DB_URL`.

Reproduce with:

```bash
MODEL_MODE=mock python -m pytest tests/test_evaluation_v2.py tests/test_properties.py tests/test_devops_domain.py -q
python scripts/run_attack_round.py
```

`scripts/run_attack_round.py` replays the seven attack documents through the
canonical application Gate and records each fixture hash. `scripts/bench_gate.py`
records Python version, platform, mode, iterations,
average, p50, and p95. CI uses hosted runners with Python 3.11/3.12,
PostgreSQL 16, and `MODEL_MODE=mock`. Pipeline replay latency must not be
confused with pure Gate latency. No external model API is used by these tests.

## CI evidence

The post-synchronization GitHub Actions run `43286591283` passed on both
Python 3.11 and 3.12. Each job reported `111 passed, 1 skipped`, with 79%
coverage. The live PostgreSQL checks were executed, including the RLS check,
the database-backed kill-switch check, the atomic capability-consumption race,
the 18-case v2 corpus, and the seven-fixture attack round. The seven attack
fixtures were all reported `PASS` and seven decisions were persisted. The sole
skip was `tests/integration/test_resilience.py::test_postgres_restart_resilience`,
which requires the separately provisioned `ROF12_TEST_DATABASE_URL`; the CI
workflow intentionally does not define that external restart-test database.
