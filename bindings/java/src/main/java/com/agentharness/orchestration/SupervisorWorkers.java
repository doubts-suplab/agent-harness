package com.agentharness.orchestration;

import com.agentharness.Agent;
import com.agentharness.Harness;
import com.agentharness.ToolRegistrationException;
import com.agentharness.model.AgentInput;
import com.agentharness.model.AgentOutput;
import com.agentharness.model.DecisionAction;
import com.agentharness.model.Decisions;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Supervisor + Workers orchestration (harness-protocol.md §6.3, ADR-0007) — the primary multi-step
 * pattern. The supervisor holds NO tool permissions (T-4). The run has two phases:
 *
 * <ol>
 *   <li><b>Planning turn.</b> The supervisor is invoked <em>through the harness</em>, so its planning
 *       decision passes the confidence gate, kill switch, and audit like any other invocation (O-1) —
 *       it just cannot touch tools. A {@code BLOCK}/{@code DEFER} decision <b>halts delegation</b>: no
 *       workers run. Otherwise the supervisor may select which workers to engage.</li>
 *   <li><b>Delegation.</b> Selected workers are each invoked through the harness (gate + registry
 *       individually) and their decisions are reconciled via the Decision Hierarchy (§3.3).</li>
 * </ol>
 *
 * <p>Worker selection is optional: a supervisor that also implements {@link Planner} chooses a subset;
 * a plain supervisor delegates to all workers.
 */
public final class SupervisorWorkers {

    /** A supervisor decision in this set stops the orchestration before any worker runs (spec §6.3). */
    private static final Set<DecisionAction> HALT = Set.of(DecisionAction.BLOCK, DecisionAction.DEFER);

    private final Harness harness;
    private final Agent supervisor;
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
        this.supervisor = supervisor;
        this.workers = List.copyOf(workers);
    }

    public OrchestrationResult run(AgentInput request) {
        // Phase 1 — governed planning turn. The supervisor reasons about the task under the harness.
        AgentOutput supervisorOutput = harness.invoke(supervisor, request);
        DecisionAction planAction = supervisorOutput.decision().action();

        // A halting supervisor decision stops the orchestration before any worker side effect.
        if (HALT.contains(planAction)) {
            return new OrchestrationResult(planAction, Map.of(), supervisorOutput, List.of(), true);
        }

        // Phase 2 — delegation. Select workers (all, unless the supervisor is a Planner).
        Map<String, Agent> workersByName = new LinkedHashMap<>();
        for (Agent w : workers) {
            workersByName.put(w.name(), w);
        }
        List<String> selected = select(request, new ArrayList<>(workersByName.keySet()));

        Map<String, AgentOutput> outputs = new LinkedHashMap<>();
        for (String name : selected) {
            outputs.put(name, harness.invoke(workersByName.get(name), request));
        }

        // Reconcile the workers that acted; with no delegation, the supervisor's own action stands.
        List<DecisionAction> actions = outputs.isEmpty()
                ? List.of(planAction)
                : outputs.values().stream().map(o -> o.decision().action()).toList();
        DecisionAction reconciled = Decisions.reconcile(actions);

        Map<String, AgentOutput> ordered = Collections.unmodifiableMap(new LinkedHashMap<>(outputs));
        return new OrchestrationResult(reconciled, ordered, supervisorOutput, List.copyOf(selected), false);
    }

    private List<String> select(AgentInput request, List<String> workerNames) {
        if (supervisor instanceof Planner planner) {
            List<String> chosen = planner.plan(request, List.copyOf(workerNames));
            // Constrain to real workers; the supervisor cannot invent or reorder beyond the roster.
            return chosen.stream().filter(workerNames::contains).toList();
        }
        return workerNames;
    }
}
