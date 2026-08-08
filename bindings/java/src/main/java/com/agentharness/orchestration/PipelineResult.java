package com.agentharness.orchestration;

import com.agentharness.model.AgentOutput;
import com.agentharness.model.DecisionAction;
import com.agentharness.model.Decisions;

import java.util.Map;

/**
 * The outcome of a sequential {@link Pipeline} run (harness-protocol.md §6.1).
 *
 * @param finalAction       the action of the last stage that ran (the short-circuiting stage, if any)
 * @param stageOutputs      per-stage outputs in execution order
 * @param shortCircuitedAt  the name of the stage that stopped the pipeline, or {@code null} if it ran to completion
 */
public record PipelineResult(DecisionAction finalAction, Map<String, AgentOutput> stageOutputs,
                             String shortCircuitedAt) {

    /** The safest action across every stage that actually ran (spec §3.3). */
    public DecisionAction reconciledAction() {
        return Decisions.reconcile(stageOutputs.values().stream().map(o -> o.decision().action()).toList());
    }

    public boolean anyAutoEnforced() {
        return stageOutputs.values().stream().anyMatch(o -> o.decision().autoEnforced());
    }
}
