package com.agentharness.orchestration;

import com.agentharness.model.AgentOutput;
import com.agentharness.model.DecisionAction;

import java.util.List;
import java.util.Map;

/**
 * The result of a {@link SupervisorWorkers} run (harness-protocol.md §6.3).
 *
 * @param reconciledAction  the reconciled worker action (or the supervisor's action if it halted /
 *                          delegated to nobody)
 * @param workerOutputs     per-worker outputs, in delegation order
 * @param supervisorOutput  the supervisor's governed planning-turn output, or {@code null}
 * @param delegated         the worker names the supervisor delegated to
 * @param halted            true if the supervisor halted before any worker ran (BLOCK/DEFER)
 */
public record OrchestrationResult(DecisionAction reconciledAction, Map<String, AgentOutput> workerOutputs,
                                  AgentOutput supervisorOutput, List<String> delegated, boolean halted) {

    public boolean anyAutoEnforced() {
        return workerOutputs.values().stream().anyMatch(o -> o.decision().autoEnforced());
    }
}
