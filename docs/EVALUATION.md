# ROF12 evaluation methodology

The v2 adversarial corpus contains 7 original vectors plus 18 additional
synthetic vectors (25 total). The expected decision and reason for every new
vector are in `attacks/v2_manifest.json`. The legitimate corpus contains 20
synthetic clean-document records. Its measured false-positive rate is
`0/20 = 0%` for the deterministic fixture classifier; this is a lab result,
not a production accuracy claim.

Reproduce with:

```bash
MODEL_MODE=mock python -m pytest tests/test_evaluation_v2.py tests/test_properties.py tests/test_devops_domain.py -q
python scripts/run_attack_round.py
```

`scripts/bench_gate.py` records Python version, platform, mode, iterations,
average, p50, and p95. CI uses hosted runners with Python 3.11/3.12,
PostgreSQL 16, and `MODEL_MODE=mock`. Pipeline replay latency must not be
confused with pure Gate latency. No external model API is used by these tests.
