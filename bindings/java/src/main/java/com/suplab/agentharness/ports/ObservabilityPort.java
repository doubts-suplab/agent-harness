package com.suplab.agentharness.ports;

/**
 * Per-invocation metrics + counters (harness-protocol.md §7.5, §4.2). MUST expose the
 * {@code confidence_gate_bypass_total} counter, which must stay 0.
 */
public interface ObservabilityPort {

    void emit(InvocationMetric metric);

    void incrementCounter(String name, int value);

    default void incrementCounter(String name) {
        incrementCounter(name, 1);
    }

    record InvocationMetric(String agentName, String action, double confidence,
                            double durationMs, String outcome, String correlationId) {
    }
}
