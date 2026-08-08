package com.agentharness.orchestration;

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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BiFunction;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Orchestration-pattern tests (harness-protocol.md §6). Every stage still passes the gate + registry (O-1). */
class OrchestrationTest {

    private static final Set<DecisionAction> ALL = Set.of(
            DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.BLOCK,
            DecisionAction.SUGGEST, DecisionAction.DEFER);

    private static final AgentInput REQ =
            new AgentInput("t1", "u1", Map.of("task", "demo"), Map.of("correlationId", "corr-1"));

    private ToolRegistry registry;
    private InMemoryAudit audit;
    private InMemoryHumanReview review;
    private InMemoryObservability obs;
    private InMemoryKillSwitch kill;
    private Harness harness;

    @BeforeEach
    void setUp() {
        registry = new ToolRegistry();
        audit = new InMemoryAudit();
        review = new InMemoryHumanReview();
        obs = new InMemoryObservability();
        kill = new InMemoryKillSwitch();
        harness = new Harness(registry, audit, review, obs, kill, new ConfidenceGate());
    }

    private static Agent agent(String name, BiFunction<AgentInput, ToolInvoker, Decision> decide) {
        return new StubAgent(name, AuthorityLevel.BLOCK, ALL, decide);
    }

    private static Agent agent(String name, AuthorityLevel authority,
                              BiFunction<AgentInput, ToolInvoker, Decision> decide) {
        return new StubAgent(name, authority, ALL, decide);
    }

    private static Agent fixed(String name, DecisionAction action, double confidence) {
        return agent(name, (in, tools) -> Decision.propose(action, confidence, "because"));
    }

    private static Agent fixed(String name, AuthorityLevel authority, DecisionAction action, double confidence) {
        return agent(name, authority, (in, tools) -> Decision.propose(action, confidence, "because"));
    }

    /** Local test agent (the package-private {@code FakeAgent} lives in a different test package). */
    private record StubAgent(String name, AuthorityLevel authorityLevel, Set<DecisionAction> capabilities,
                             BiFunction<AgentInput, ToolInvoker, Decision> decide) implements Agent {
        @Override
        public Decision decide(AgentInput input, ToolInvoker tools) {
            return decide.apply(input, tools);
        }
    }

    // -- Pipeline (§6.1) ---------------------------------------------------
    @Test
    void pipelineRunsAllStagesInOrder() {
        List<String> order = new ArrayList<>();
        List<Agent> stages = List.of(
                agent("s1", (in, t) -> { order.add("s1"); return Decision.propose(DecisionAction.ALLOW, 0.9, "ok"); }),
                agent("s2", (in, t) -> { order.add("s2"); return Decision.propose(DecisionAction.ALLOW, 0.9, "ok"); }),
                agent("s3", (in, t) -> { order.add("s3"); return Decision.propose(DecisionAction.ALLOW, 0.9, "ok"); }));
        PipelineResult result = new Pipeline(harness, stages).run(REQ);
        assertEquals(List.of("s1", "s2", "s3"), order);
        assertEquals(DecisionAction.ALLOW, result.finalAction());
        assertNull(result.shortCircuitedAt());
    }

    @Test
    void pipelinePassesPriorDecisionIntoNextStageContext() {
        Map<String, Object> seen = new java.util.HashMap<>();
        List<Agent> stages = List.of(
                agent("s1", (in, t) -> Decision.propose(DecisionAction.ALERT, 0.9, "raise an alert")),
                agent("s2", (in, t) -> {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> p = (Map<String, Object>) in.context().get("pipeline");
                    seen.putAll(p);
                    return Decision.propose(DecisionAction.ALLOW, 0.9, "ok");
                }));
        new Pipeline(harness, stages).run(REQ);
        assertEquals("s1", seen.get("prior_stage"));
        assertEquals("ALERT", seen.get("prior_action"));
        assertEquals(0.9, seen.get("prior_confidence"));
        assertEquals("raise an alert", seen.get("prior_rationale"));
    }

    @Test
    void pipelineShortCircuitsOnBlock() {
        List<String> ran = new ArrayList<>();
        List<Agent> stages = List.of(
                agent("s1", (in, t) -> { ran.add("s1"); return Decision.propose(DecisionAction.ALLOW, 0.9, "ok"); }),
                agent("s2", (in, t) -> { ran.add("s2"); return Decision.propose(DecisionAction.BLOCK, 0.99, "stop"); }),
                agent("s3", (in, t) -> { ran.add("s3"); return Decision.propose(DecisionAction.ALLOW, 0.9, "ok"); }));
        PipelineResult result = new Pipeline(harness, stages).run(REQ);
        assertEquals(List.of("s1", "s2"), ran); // s3 never runs
        assertEquals("s2", result.shortCircuitedAt());
        assertEquals(DecisionAction.BLOCK, result.finalAction());
    }

    @Test
    void pipelineEachStagePassesGateBypassZero() {
        List<Agent> stages = List.of(
                fixed("s1", DecisionAction.ALERT, 0.96),
                fixed("s2", DecisionAction.ALLOW, 0.9));
        new Pipeline(harness, stages).run(REQ);
        assertEquals(0, obs.counter(Harness.BYPASS_COUNTER));
        assertEquals(2, audit.entries().size()); // O-1: each stage went through the harness
    }

    @Test
    void pipelineReconciledActionIsSafestSeen() {
        List<Agent> stages = List.of(
                fixed("s1", DecisionAction.ALLOW, 0.9),
                fixed("s2", DecisionAction.ALERT, 0.9));
        assertEquals(DecisionAction.ALERT, new Pipeline(harness, stages).run(REQ).reconciledAction());
    }

    @Test
    void pipelineRequiresAtLeastOneStage() {
        assertThrows(IllegalArgumentException.class, () -> new Pipeline(harness, List.of()));
    }
}
