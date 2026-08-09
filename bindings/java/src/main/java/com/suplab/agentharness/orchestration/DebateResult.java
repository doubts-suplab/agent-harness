package com.suplab.agentharness.orchestration;

import com.suplab.agentharness.model.AgentOutput;
import com.suplab.agentharness.model.DecisionAction;

import java.util.Map;

/**
 * The reconciled outcome of a {@link Debate} (harness-protocol.md §6.4).
 *
 * @param consensusAction    the reconciled action
 * @param rule               the consensus rule applied
 * @param participantOutputs per-participant outputs, in participation order
 * @param tie                true if a {@code MAJORITY} vote tied and resolved to {@code DEFER}
 */
public record DebateResult(DecisionAction consensusAction, ConsensusRule rule,
                           Map<String, AgentOutput> participantOutputs, boolean tie) {

    public boolean anyAutoEnforced() {
        return participantOutputs.values().stream().anyMatch(o -> o.decision().autoEnforced());
    }
}
