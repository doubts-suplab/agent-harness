package com.agentharness.adapters;

import com.agentharness.ports.ObservabilityPort;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/** In-memory metrics + counters (harness-protocol.md §7.5, §4.2). */
public final class InMemoryObservability implements ObservabilityPort {

    private final List<InvocationMetric> metrics = new CopyOnWriteArrayList<>();
    private final Map<String, Integer> counters = new ConcurrentHashMap<>();

    @Override
    public void emit(InvocationMetric metric) {
        metrics.add(metric);
    }

    @Override
    public void incrementCounter(String name, int value) {
        counters.merge(name, value, Integer::sum);
    }

    public int counter(String name) {
        return counters.getOrDefault(name, 0);
    }

    public List<InvocationMetric> metrics() {
        return List.copyOf(metrics);
    }
}
