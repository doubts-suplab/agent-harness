package com.agentharness.examples;

import com.agentharness.Agent;
import com.agentharness.ConfidenceGate;
import com.agentharness.Harness;
import com.agentharness.ToolInvoker;
import com.agentharness.ToolRegistry;
import com.agentharness.adapters.InMemoryAudit;
import com.agentharness.adapters.InMemoryHumanReview;
import com.agentharness.adapters.InMemoryKillSwitch;
import com.agentharness.adapters.InMemoryObservability;
import com.agentharness.model.AgentInput;
import com.agentharness.model.AuthorityLevel;
import com.agentharness.model.Decision;
import com.agentharness.model.DecisionAction;
import com.agentharness.orchestration.ConsensusRule;
import com.agentharness.orchestration.Debate;
import com.agentharness.orchestration.FanOut;
import com.agentharness.orchestration.Pipeline;
import com.agentharness.orchestration.SupervisorWorkers;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Multi-agent orchestration example (harness-protocol.md §6) — the Java counterpart to
 * {@code examples/orchestration.py}. Runs three tiny agents under each pattern; every agent goes
 * through the harness, so {@code confidence_gate_bypass_total} stays 0.
 *
 * <p>Run: {@code mvn -q exec:java -Dexec.mainClass=com.agentharness.examples.OrchestrationExample}
 * (or call {@link #run()} from code / a test).
 */
public final class OrchestrationExample {

    private static final Set<DecisionAction> ALL = Set.of(
            DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK, DecisionAction.DEFER);

    /** An agent that always proposes the same action/confidence. */
    private record FixedAgent(String name, DecisionAction action, double confidence) implements Agent {
        @Override
        public AuthorityLevel authorityLevel() {
            return AuthorityLevel.BLOCK;
        }

        @Override
        public Set<DecisionAction> capabilities() {
            return ALL;
        }

        @Override
        public Decision decide(AgentInput input, ToolInvoker tools) {
            return Decision.propose(action, confidence, name + " says " + action);
        }
    }

    private OrchestrationExample() {
    }

    /** Runs each pattern and returns a human-readable summary (also printed to stdout). */
    public static String run() {
        InMemoryObservability obs = new InMemoryObservability();
        Harness harness = new Harness(new ToolRegistry(), new InMemoryAudit(), new InMemoryHumanReview(),
                obs, new InMemoryKillSwitch(), new ConfidenceGate());
        AgentInput request = new AgentInput("acme", "alice", Map.of("task", "review a change"), Map.of());

        Agent allow = new FixedAgent("linter", DecisionAction.ALLOW, 0.95);
        Agent alert = new FixedAgent("risk-scanner", DecisionAction.ALERT, 0.9);
        Agent block = new FixedAgent("secrets-scanner", DecisionAction.BLOCK, 0.97);

        var pipe = new Pipeline(harness, List.of(allow, alert, block)).run(request);
        var fan = new FanOut(harness, List.of(allow, alert, block)).run(request);
        var debate = new Debate(harness, List.of(allow, alert, block), ConsensusRule.MAJORITY).run(request);
        Agent supervisor = new FixedAgent("supervisor", DecisionAction.ALLOW, 0.9);
        var sup = new SupervisorWorkers(harness, supervisor, List.of(allow, alert, block)).run(request);

        String summary = String.join("\n",
                "Pipeline   -> final=" + pipe.finalAction() + " (short-circuited at " + pipe.shortCircuitedAt() + ")",
                "Fan-out    -> reconciled=" + fan.reconciledAction() + " (safest of all workers)",
                "Debate     -> consensus=" + debate.consensusAction() + " (rule=MAJORITY, tie=" + debate.tie() + ")",
                "Supervisor -> reconciled=" + sup.reconciledAction() + " delegated=" + sup.delegated(),
                "confidence_gate_bypass_total = " + obs.counter(Harness.BYPASS_COUNTER) + "  (must be 0)");
        System.out.println(summary);
        return summary;
    }

    public static void main(String[] args) {
        run();
    }
}
