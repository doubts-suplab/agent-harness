package com.agentharness.orchestration;

import com.agentharness.model.AgentOutput;
import com.agentharness.model.DecisionAction;

import java.util.Map;

/** The result of a multi-agent orchestration (harness-protocol.md §6). */
public record OrchestrationResult(DecisionAction reconciledAction, Map<String, AgentOutput> workerOutputs) {

    public boolean anyAutoEnforced() {
        return workerOutputs.values().stream().anyMatch(o -> o.decision().autoEnforced());
    }
}
