"""OpenTelemetry ObservabilityPort exporter tests (spec §7.5) — offline via in-memory OTel exporters."""

from __future__ import annotations

import pytest

pytest.importorskip("opentelemetry.sdk")  # skip cleanly if the optional 'otel' extra isn't installed

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from halo_agent_harness import AgentInput, AuthorityLevel, BYPASS_COUNTER, DecisionAction, Harness
from halo_agent_harness.adapters.otel import OtelObservability
from halo_agent_harness.ports.governance import InvocationMetric
from conftest import FakeAgent, static_decision


def _rig():
    exporter = InMemorySpanExporter()
    tp = TracerProvider()
    tp.add_span_processor(SimpleSpanProcessor(exporter))
    reader = InMemoryMetricReader()
    mp = MeterProvider(metric_readers=[reader])
    obs = OtelObservability(tracer=tp.get_tracer("test"), meter=mp.get_meter("test"))
    return obs, exporter, reader


def _metric_names(reader) -> set[str]:
    names: set[str] = set()
    data = reader.get_metrics_data()
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                names.add(m.name)
    return names


def test_emit_records_a_span_with_attributes():
    obs, exporter, _ = _rig()
    obs.emit(InvocationMetric("gov", "BLOCK", 0.97, 12.5, "auto-enforced", "corr-1"))
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = dict(spans[0].attributes)
    assert attrs["agent.name"] == "gov"
    assert attrs["agent.action"] == "BLOCK"
    assert attrs["agent.outcome"] == "auto-enforced"
    assert attrs["correlation.id"] == "corr-1"


def test_emit_records_invocation_and_duration_metrics():
    obs, _, reader = _rig()
    obs.emit(InvocationMetric("a", "ALERT", 0.9, 5.0, "human-review", None))
    names = _metric_names(reader)
    assert "agent_invocations_total" in names
    assert "agent_invocation_duration_ms" in names


def test_increment_counter_is_exported():
    obs, _, reader = _rig()
    obs.increment_counter(BYPASS_COUNTER, 0)  # created; stays 0 in a correct system
    obs.increment_counter("custom_total", 3)
    names = _metric_names(reader)
    assert BYPASS_COUNTER in names
    assert "custom_total" in names


def test_harness_wires_the_otel_port_end_to_end():
    obs, exporter, _ = _rig()
    harness = Harness(observability=obs)
    agent = FakeAgent("a", AuthorityLevel.ALERT, frozenset({DecisionAction.ALERT}),
                      static_decision(DecisionAction.ALERT, 0.9))
    harness.invoke(agent, AgentInput("t1", "u1", metadata={"correlationId": "corr-9"}))
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert dict(spans[0].attributes)["agent.name"] == "a"
