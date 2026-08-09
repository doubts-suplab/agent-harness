"""OpenTelemetry `ObservabilityPort` exporter (spec §7.5, §4.2).

Maps each per-invocation metric to an OTel **span** (agent, action, confidence, duration, outcome,
correlation id) *and* to OTel **metrics** (an invocations counter + a duration histogram), and mirrors
harness counters — including ``confidence_gate_bypass_total`` — as OTel counters.

This adapter is **optional**: it is deliberately NOT imported by ``halo_agent_harness.adapters``, so the
OpenTelemetry SDK is only required when you import this module. Install it with the ``otel`` extra
(``pip install "agent-harness[otel]"``). Wire it with ``Harness(observability=OtelObservability(...))``.
"""

from __future__ import annotations

from ..ports.governance import InvocationMetric

_INVOCATIONS = "agent_invocations_total"
_DURATION = "agent_invocation_duration_ms"


class OtelObservability:
    """`ObservabilityPort` backed by OpenTelemetry traces + metrics.

    Pass an OTel ``Tracer`` and ``Meter`` (e.g. from your configured providers); if omitted, the global
    providers are used. Counters are created lazily and cached by name.
    """

    def __init__(self, tracer=None, meter=None, *, span_name: str = "agent.invocation") -> None:
        # Imported here so merely importing this module does not require the OTel SDK to be installed.
        from opentelemetry import metrics, trace

        self._tracer = tracer or trace.get_tracer("halo_agent_harness")
        self._meter = meter or metrics.get_meter("halo_agent_harness")
        self._span_name = span_name
        self._invocations = self._meter.create_counter(_INVOCATIONS)
        self._duration = self._meter.create_histogram(_DURATION)
        self._counters: dict = {}

    def emit(self, metric: InvocationMetric) -> None:
        attributes = {
            "agent.name": metric.agent_name,
            "agent.action": metric.action,
            "agent.confidence": metric.confidence,
            "agent.duration_ms": metric.duration_ms,
            "agent.outcome": metric.outcome,
        }
        if metric.correlation_id:
            attributes["correlation.id"] = metric.correlation_id
        # Record the already-measured invocation as a span; end immediately (timing came from the harness).
        self._tracer.start_span(self._span_name, attributes=attributes).end()

        dimensions = {"action": metric.action, "outcome": metric.outcome}
        self._invocations.add(1, dimensions)
        self._duration.record(metric.duration_ms, dimensions)

    def increment_counter(self, name: str, value: int = 1) -> None:
        counter = self._counters.get(name)
        if counter is None:
            counter = self._meter.create_counter(name)
            self._counters[name] = counter
        counter.add(value)
