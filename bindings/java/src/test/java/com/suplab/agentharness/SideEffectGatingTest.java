package com.suplab.agentharness;

import com.suplab.agentharness.adapters.InMemoryAudit;
import com.suplab.agentharness.adapters.InMemoryHumanReview;
import com.suplab.agentharness.adapters.InMemoryKillSwitch;
import com.suplab.agentharness.adapters.InMemoryObservability;
import com.suplab.agentharness.model.AgentInput;
import com.suplab.agentharness.model.AuthorityLevel;
import com.suplab.agentharness.model.Decision;
import com.suplab.agentharness.model.DecisionAction;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Side-effect gating tests (harness-protocol.md §5.3, T-5). */
class SideEffectGatingTest {

    private static final Set<DecisionAction> ALL =
            Set.of(DecisionAction.ALLOW, DecisionAction.ALERT, DecisionAction.DEFER);

    private static final AgentInput REQ =
            new AgentInput("t1", "u1", Map.of("task", "demo"), Map.of("correlationId", "corr-1"));

    private ToolRegistry registry;
    private InMemoryAudit audit;
    private Harness harness;

    @BeforeEach
    void setUp() {
        registry = new ToolRegistry();
        audit = new InMemoryAudit();
        harness = new Harness(registry, audit, new InMemoryHumanReview(),
                new InMemoryObservability(), new InMemoryKillSwitch(), new ConfidenceGate());
    }

    private static Agent toolAgent(String name, AuthorityLevel authority, String tool, Double callConfidence) {
        return new FakeAgent(name, authority, ALL, (in, tools) -> {
            if (callConfidence == null) {
                tools.call(tool, Map.of("x", 1));
            } else {
                tools.call(tool, Map.of("x", 1), callConfidence);
            }
            return Decision.propose(DecisionAction.ALLOW, 0.9, "called " + tool);
        });
    }

    private boolean deniedLogged() {
        return audit.securityEvents().stream().anyMatch(e -> e.kind().equals("side_effect_denied"));
    }

    // -- policy unit behaviour --------------------------------------------
    @Test
    void policyUngatedClassesAlwaysPass() {
        SideEffectPolicy policy = SideEffectPolicy.defaults();
        for (String cls : new String[]{"none", "read", null}) {
            assertTrue(policy.permits(cls, null, AuthorityLevel.OBSERVE));
        }
    }

    @Test
    void policyGatedRequiresThreshold() {
        SideEffectPolicy policy = SideEffectPolicy.defaults();
        assertFalse(policy.permits("write", 0.84, AuthorityLevel.ALERT));
        assertTrue(policy.permits("write", 0.85, AuthorityLevel.ALERT));
        assertFalse(policy.permits("external", 0.94, AuthorityLevel.BLOCK));
        assertTrue(policy.permits("external", 0.95, AuthorityLevel.BLOCK));
    }

    @Test
    void policyObserveAgentNeverPerformsSideEffects() {
        SideEffectPolicy policy = SideEffectPolicy.defaults();
        assertFalse(policy.permits("write", 1.0, AuthorityLevel.OBSERVE));
        assertFalse(policy.permits("external", 1.0, AuthorityLevel.OBSERVE));
    }

    // -- harness-enforced gating ------------------------------------------
    @Test
    void readToolIsNotGated() {
        registry.registerTool("lookup", "read", a -> "row");
        registry.grant("a", Set.of("lookup"));
        harness.invoke(toolAgent("a", AuthorityLevel.ALERT, "lookup", null), REQ);
        assertTrue(audit.securityEvents().isEmpty());
    }

    @Test
    void writeToolBelowThresholdRefusedBeforeExecution() {
        AtomicInteger executed = new AtomicInteger();
        registry.registerTool("save", "write", a -> { executed.incrementAndGet(); return "ok"; });
        registry.grant("a", Set.of("save"));
        var out = harness.invoke(toolAgent("a", AuthorityLevel.ALERT, "save", 0.5), REQ);
        assertEquals(0, executed.get()); // the side effect never happened
        assertEquals(DecisionAction.DEFER, out.decision().action()); // safe failure default
        assertFalse(out.decision().autoEnforced());
        assertTrue(deniedLogged());
    }

    @Test
    void writeToolAtThresholdExecutes() {
        AtomicInteger executed = new AtomicInteger();
        registry.registerTool("save", "write", a -> { executed.incrementAndGet(); return "ok"; });
        registry.grant("a", Set.of("save"));
        var out = harness.invoke(toolAgent("a", AuthorityLevel.ALERT, "save", 0.85), REQ);
        assertEquals(1, executed.get());
        assertEquals(DecisionAction.ALLOW, out.decision().action());
        assertTrue(audit.securityEvents().isEmpty());
    }

    @Test
    void externalToolRequiresHigherConfidence() {
        AtomicInteger executed = new AtomicInteger();
        registry.registerTool("api", "external", a -> { executed.incrementAndGet(); return "ok"; });
        registry.grant("a", Set.of("api"));
        // 0.85 clears write but not external (0.95).
        var out = harness.invoke(toolAgent("a", AuthorityLevel.BLOCK, "api", 0.85), REQ);
        assertEquals(0, executed.get());
        assertEquals(DecisionAction.DEFER, out.decision().action());
        assertTrue(deniedLogged());
    }

    @Test
    void observeAgentCannotCallWriteTool() {
        AtomicInteger executed = new AtomicInteger();
        registry.registerTool("save", "write", a -> { executed.incrementAndGet(); return "ok"; });
        registry.grant("obs", Set.of("save"));
        harness.invoke(toolAgent("obs", AuthorityLevel.OBSERVE, "save", 1.0), REQ);
        assertEquals(0, executed.get()); // even at confidence 1.0, a read-only agent may not write
        assertTrue(deniedLogged());
    }

    @Test
    void customPolicyThresholdsAreHonoured() {
        registry.registerTool("save", "write", a -> "ok");
        registry.grant("a", Set.of("save"));
        Harness custom = new Harness(registry, audit, new InMemoryHumanReview(),
                new InMemoryObservability(), new InMemoryKillSwitch(), new ConfidenceGate(),
                new SideEffectPolicy(0.6, 0.95));
        var out = custom.invoke(toolAgent("a", AuthorityLevel.ALERT, "save", 0.65), REQ);
        assertEquals(DecisionAction.ALLOW, out.decision().action()); // 0.65 clears the lowered 0.6 bar
        assertTrue(audit.securityEvents().isEmpty());
    }
}
