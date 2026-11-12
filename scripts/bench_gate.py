"""Measure deterministic SecurityGate latency and record reproducible metadata."""

from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from types import SimpleNamespace

from app.security.security_gate import SecurityGate


def measure(iterations: int) -> list[float]:
    gate = SecurityGate()
    context = SimpleNamespace(
        user_id="user_001", tenant_id="tenant_001", membership_status="ACTIVE"
    )
    request = SimpleNamespace(tool_name="refund_service")
    capability = SimpleNamespace(valid=True, reasons=())
    provenance = SimpleNamespace(is_tainted=False)
    risk = SimpleNamespace(risk_level="LOW")
    verity = SimpleNamespace(
        checks={"V2": True, "V4": True, "V5": True}, approval_required=False
    )
    state = SimpleNamespace(active=False)
    timings: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        result = gate.evaluate(
            context, request, capability, provenance, risk, verity, state
        )
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        if result.decision.value != "ALLOW":
            raise RuntimeError(f"unexpected benchmark decision: {result.decision}")
        timings.append(elapsed_ms)
    return timings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--iterations", type=int, default=1000)
    parser.add_argument("--output", default="docs/BENCHMARKS.md")
    args = parser.parse_args()
    if args.iterations < 1:
        raise SystemExit("iterations must be positive")
    timings = measure(args.iterations)
    ordered = sorted(timings)
    p50 = statistics.median(ordered)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    average = statistics.fmean(ordered)
    now = datetime.now(timezone.utc).isoformat()
    report = f"""# ROF12 Gate benchmarks

Last measured: `{now}`
Mode: `{os.getenv('MODEL_MODE', 'mock')}`
Python: `{sys.version.split()[0]}`
Platform: `{platform.platform()}`
Iterations: `{args.iterations}` deterministic `SecurityGate.evaluate()` calls
Decision: `ALLOW` for every iteration

| Metric | Milliseconds |
|---|---:|
| Average | {average:.4f} |
| p50 | {p50:.4f} |
| p95 | {p95:.4f} |
"""
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(report)
    print(report, end="")


if __name__ == "__main__":
    main()
