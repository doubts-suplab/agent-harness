package com.suplab.agentharness.orchestration;

import com.suplab.agentharness.model.AgentOutput;
import com.suplab.agentharness.model.DecisionAction;
import com.suplab.agentharness.model.Decisions;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/** The aggregated outcome of a parallel {@link FanOut} (harness-protocol.md §6.2). */
public record FanOutResult(DecisionAction reconciledAction, Map<String, AgentOutput> workerOutputs) {

    /** Reconcile worker outputs toward the safest action (spec §3.3). Worker order is preserved. */
    static FanOutResult of(Map<String, AgentOutput> outputs) {
        DecisionAction reconciled = Decisions.reconcile(
                outputs.values().stream().map(o -> o.decision().action()).toList());
        // Preserve insertion order (Map.copyOf does not) so worker_outputs is order-stable.
        Map<String, AgentOutput> ordered = Collections.unmodifiableMap(new LinkedHashMap<>(outputs));
        return new FanOutResult(reconciled, ordered);
    }

    public boolean anyAutoEnforced() {
        return workerOutputs.values().stream().anyMatch(o -> o.decision().autoEnforced());
    }
}
