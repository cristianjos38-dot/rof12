# ROF12 benchmarks

## Decisión pura del Gate

Last measured: `2026-11-09T22:05:25.500323+00:00`
Mode: `mock`
Python: `3.11.15`
Platform: `macOS-26.6.2-arm64-arm-64bit`
Method: 1,000 in-memory `SecurityGate.evaluate()` calls with valid synthetic
context, capability, provenance and VerityFlow dimensions.
Decision: `ALLOW` for every iteration

| Metric | Milliseconds |
|---|---:|
| Average | 0.0021 |
| p50 | 0.0021 |
| p95 | 0.0022 |

## Pipeline protegido por documento

The ignored replay artifact `demo_benchmark.json` contains seven protected
document rows. Its recorded protected latencies sum to 25.473 ms, giving an
average of **3.639 ms per document**. This is the document pipeline measurement
in that artifact, not the pure Gate measurement above. The artifact records no
host, Python version or `MODEL_MODE`, so those provenance fields are **unknown**
and the 3.639 ms figure is not presented as a reproducible hardware-certified
baseline until a fresh database-backed replay records them.

The artifact's total replay time is 5,375.756 ms for 14 persisted rows. It is
not used as a claim about per-document Gate latency.
