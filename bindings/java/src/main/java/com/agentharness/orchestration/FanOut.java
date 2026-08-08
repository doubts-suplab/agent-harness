package com.agentharness.orchestration;

import com.agentharness.Agent;
import com.agentharness.Harness;
import com.agentharness.model.AgentInput;
import com.agentharness.model.AgentOutput;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

/**
 * Parallel Fan-out orchestration (harness-protocol.md §6.2).
 *
 * <p>Independent worker agents run concurrently over the <em>same</em> {@link AgentInput}; the harness
 * reconciles their decisions with the Decision Hierarchy ({@code BLOCK} wins, then {@code ALERT}, …).
 * Every worker is invoked through {@link Harness#invoke}, so each passes the confidence gate and tool
 * registry individually (O-1). The aggregation policy is <em>collect-and-reconcile</em>: every worker
 * runs and the safest action wins.
 *
 * <p>Concurrency: workers run on a fixed thread pool. The reference in-memory adapters are thread-safe
 * ({@code CopyOnWriteArrayList} + {@code ConcurrentHashMap}), so {@code confidence_gate_bypass_total}
 * accumulates correctly.
 */
public final class FanOut {

    private final Harness harness;
    private final List<Agent> workers;

    public FanOut(Harness harness, List<Agent> workers) {
        if (workers == null || workers.isEmpty()) {
            throw new IllegalArgumentException("fan-out requires at least one worker agent");
        }
        this.harness = harness;
        this.workers = List.copyOf(workers);
    }

    public FanOutResult run(AgentInput request) {
        // Submit every worker; collect results keyed by worker so the mapping is order-stable
        // regardless of completion order.
        Map<String, Future<AgentOutput>> futures = new LinkedHashMap<>();
        try (ExecutorService pool = Executors.newFixedThreadPool(workers.size())) {
            for (Agent worker : workers) {
                futures.put(worker.name(), pool.submit(() -> harness.invoke(worker, request)));
            }
            Map<String, AgentOutput> outputs = new LinkedHashMap<>();
            for (Map.Entry<String, Future<AgentOutput>> e : futures.entrySet()) {
                outputs.put(e.getKey(), await(e.getValue()));
            }
            return FanOutResult.of(outputs);
        }
    }

    private static AgentOutput await(Future<AgentOutput> future) {
        try {
            return future.get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("fan-out interrupted", e);
        } catch (ExecutionException e) {
            // Harness.invoke never throws for agent failures (it returns a safe decision); a throw here
            // is an orchestration-level fault, surfaced rather than silently swallowed.
            throw new IllegalStateException("fan-out worker failed", e.getCause());
        }
    }
}
