package com.agentharness.orchestration;

import com.agentharness.Agent;
import com.agentharness.Harness;
import com.agentharness.model.AgentInput;
import com.agentharness.model.AgentOutput;
import com.agentharness.model.DecisionAction;
import com.agentharness.model.Decisions;

import java.util.Collections;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Debate / Consensus orchestration (harness-protocol.md §6.4).
 *
 * <p>Multiple agents produce competing decisions over the same {@link AgentInput}; a
 * {@link ConsensusRule} reconciles them. Every participant is invoked through {@link Harness#invoke},
 * so each passes the confidence gate and tool registry individually (O-1).
 *
 * <p><b>Safety floor (invariant).</b> Consensus can never <em>raise</em> authority above the strictest
 * participant: the consensus action's severity never exceeds the strictest action any participant
 * actually proposed. Every rule chooses among proposed actions, so this holds by construction; it is
 * enforced defensively here and asserted by tests.
 */
public final class Debate {

    private final Harness harness;
    private final List<Agent> participants;
    private final ConsensusRule rule;

    public Debate(Harness harness, List<Agent> participants, ConsensusRule rule) {
        if (participants == null || participants.isEmpty()) {
            throw new IllegalArgumentException("a debate requires at least one participant");
        }
        this.harness = harness;
        this.participants = List.copyOf(participants);
        this.rule = rule == null ? ConsensusRule.SAFEST : rule;
    }

    /** A debate under the default {@code SAFEST} rule. */
    public Debate(Harness harness, List<Agent> participants) {
        this(harness, participants, ConsensusRule.SAFEST);
    }

    public DebateResult run(AgentInput request) {
        Map<String, AgentOutput> outputs = new LinkedHashMap<>();
        for (Agent p : participants) {
            outputs.put(p.name(), harness.invoke(p, request));
        }
        List<DecisionAction> actions = outputs.values().stream().map(o -> o.decision().action()).toList();

        Consensus consensus = decide(actions);
        DecisionAction action = consensus.action();

        // Safety floor (§6.4): never exceed the strictest action any participant proposed.
        DecisionAction ceiling = Decisions.reconcile(actions);
        if (Decisions.actionPrecedence(action) > Decisions.actionPrecedence(ceiling)) {
            action = ceiling;
        }

        Map<String, AgentOutput> ordered = Collections.unmodifiableMap(new LinkedHashMap<>(outputs));
        return new DebateResult(action, rule, ordered, consensus.tie());
    }

    private record Consensus(DecisionAction action, boolean tie) {
    }

    private Consensus decide(List<DecisionAction> actions) {
        if (rule == ConsensusRule.SAFEST) {
            return new Consensus(Decisions.reconcile(actions), false);
        }
        // MAJORITY: highest vote count wins; a tie for the top count resolves to DEFER.
        Map<DecisionAction, Integer> counts = new EnumMap<>(DecisionAction.class);
        for (DecisionAction a : actions) {
            counts.merge(a, 1, Integer::sum);
        }
        int top = Collections.max(counts.values());
        List<DecisionAction> winners = counts.entrySet().stream()
                .filter(e -> e.getValue() == top).map(Map.Entry::getKey).toList();
        if (winners.size() == 1) {
            return new Consensus(winners.get(0), false);
        }
        return new Consensus(DecisionAction.DEFER, true);
    }
}
