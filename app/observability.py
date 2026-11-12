"""Optional OpenTelemetry hooks with a safe no-exporter default."""

from __future__ import annotations

import os
from collections import Counter
from time import perf_counter
from opentelemetry import trace

decision_counts: Counter[str] = Counter()
_tracer = trace.get_tracer("rof12.security_gate")


def configure_telemetry() -> None:
    """Enable OTLP only when explicitly configured; otherwise remain no-op."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider = TracerProvider(resource=Resource.create({"service.name": "rof12"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
    except ImportError:
        # The API remains operational if only opentelemetry-api is installed.
        return


def observe_decision(context, result):
    started = perf_counter()
    decision = result.decision.value
    decision_counts[decision] += 1
    with _tracer.start_as_current_span("rof12.security_gate.evaluate") as span:
        span.set_attribute("rof12.decision", decision)
        span.set_attribute("rof12.tenant_id", str(getattr(context, "tenant_id", "")))
        span.set_attribute("rof12.policy_version", os.getenv("ROF12_POLICY_VERSION", "v1"))
        span.set_attribute("rof12.latency_ms", (perf_counter() - started) * 1000)
