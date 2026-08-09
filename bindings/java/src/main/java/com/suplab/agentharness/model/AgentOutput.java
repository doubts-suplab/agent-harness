package com.suplab.agentharness.model;

import java.time.Instant;

/** One invocation's output envelope (harness-protocol.md §2.2). */
public record AgentOutput(Decision decision, String agentName, Instant executedAt) {

    public static AgentOutput now(Decision decision, String agentName) {
        return new AgentOutput(decision, agentName, Instant.now());
    }
}
