package com.suplab.agentharness.adapters;

import com.suplab.agentharness.adapters.InMemoryHumanReview.QueuedReview;
import com.suplab.agentharness.ports.ObservabilityPort;

import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Human-review SLA monitor (harness-protocol.md §7.4).
 *
 * <p>Sweeps a review queue for items past their SLA deadline and emits a breach counter through the
 * {@link ObservabilityPort}. Each breached item is counted at most once, so repeated sweeps are
 * idempotent. This is the enforcement/monitoring hook the spec calls for; escalation policy (paging,
 * reassignment) sits above this signal.
 */
public final class SlaMonitor {

    /** Emitted once per review item that breaches its SLA (spec §7.4). */
    public static final String HUMAN_REVIEW_SLA_BREACH = "human_review_sla_breach_total";

    private final InMemoryHumanReview queue;
    private final ObservabilityPort observability;
    private final Set<Long> counted = ConcurrentHashMap.newKeySet();

    public SlaMonitor(InMemoryHumanReview queue, ObservabilityPort observability) {
        this.queue = queue;
        this.observability = observability;
    }

    /** Return currently-overdue items; increment the breach counter for newly-breached ones. */
    public List<QueuedReview> sweep(Instant now) {
        List<QueuedReview> breached = queue.overdue(now);
        for (QueuedReview q : breached) {
            if (counted.add(q.id())) {
                observability.incrementCounter(HUMAN_REVIEW_SLA_BREACH, 1);
            }
        }
        return breached;
    }

    public int breachCount() {
        return counted.size();
    }
}
