package com.agentharness.orchestration;

import com.agentharness.Agent;
import com.agentharness.Harness;
import com.agentharness.ToolRegistrationException;
import com.agentharness.model.AgentInput;
import com.agentharness.model.AgentOutput;
import com.agentharness.model.DecisionAction;
import com.agentharness.model.Decisions;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Supervisor + Workers orchestration (harness-protocol.md §6.3, ADR-0007) — the primary multi-step
 * pattern. The supervisor holds NO tool permissions (T-4). Every worker is invoked through the harness,
 * so each passes the confidence gate and tool registry individually (O-1). Worker decisions are
 * reconciled via the Decision Hierarchy (spec §3.3).
 *
 * <p>This is a superset of grid's current single-pass fan-out: grid reconciles severity in
 * {@code OrchestrationResult}; here the supervisor is an explicit, tool-less coordinator.
 */
public final class SupervisorWorkers {

    private final Harness harness;
    private final List<Agent> workers;

    public SupervisorWorkers(Harness harness, Agent supervisor, List<Agent> workers) {
        if (!harness.registry().allowlist(supervisor.name()).isEmpty()) {
            throw new ToolRegistrationException(
                    "supervisor '" + supervisor.name() + "' MUST hold no tool permissions (spec §6.3 T-4)");
        }
        if (workers == null || workers.isEmpty()) {
            throw new IllegalArgumentException("at least one worker agent is required");
        }
        this.harness = harness;
        this.workers = List.copyOf(workers);
    }

    public OrchestrationResult run(AgentInput request) {
        Map<String, AgentOutput> outputs = new LinkedHashMap<>();
        for (Agent worker : workers) {
            outputs.put(worker.name(), harness.invoke(worker, request));
        }
        DecisionAction reconciled = Decisions.reconcile(
                outputs.values().stream().map(o -> o.decision().action()).toList());
        return new OrchestrationResult(reconciled, Map.copyOf(outputs));
    }
}
