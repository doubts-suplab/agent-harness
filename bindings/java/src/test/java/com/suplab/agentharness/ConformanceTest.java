package com.suplab.agentharness;

import com.suplab.agentharness.adapters.InMemoryAudit;
import com.suplab.agentharness.adapters.InMemoryHumanReview;
import com.suplab.agentharness.adapters.InMemoryKillSwitch;
import com.suplab.agentharness.adapters.InMemoryObservability;
import com.suplab.agentharness.model.AgentInput;
import com.suplab.agentharness.model.AgentOutput;
import com.suplab.agentharness.model.AuthorityLevel;
import com.suplab.agentharness.model.Decision;
import com.suplab.agentharness.model.DecisionAction;
import com.suplab.agentharness.model.Decisions;
import com.suplab.agentharness.orchestration.SupervisorWorkers;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Conformance suite — maps 1:1 to harness-protocol.md §9. Each test cites its checklist item. */
class ConformanceTest {

    private ToolRegistry registry;
    private InMemoryAudit audit;
    private InMemoryHumanReview review;
    private InMemoryObservability obs;
    private InMemoryKillSwitch kill;
    private Harness harness;

    private static final AgentInput REQ =
            new AgentInput("t1", "u1", Map.of("task", "demo"), Map.of("correlationId", "corr-1"));

    @BeforeEach
    void setUp() {
        registry = new ToolRegistry();
        audit = new InMemoryAudit();
        review = new InMemoryHumanReview();
        obs = new InMemoryObservability();
        kill = new InMemoryKillSwitch();
        harness = new Harness(registry, audit, review, obs, kill, new ConfidenceGate());
    }

    // §9 — Envelope: one input in, one output out; tenant/user validated (§2) ------------------
    @Test
    void envelopeRoundtrip() {
        Agent a = FakeAgent.of("a", AuthorityLevel.ALERT, Set.of(DecisionAction.ALERT), DecisionAction.ALERT, 0.9);
        AgentOutput out = harness.invoke(a, REQ);
        assertEquals("a", out.agentName());
        assertEquals(DecisionAction.ALERT, out.decision().action());
    }

    @Test
    void unscopedInvocationIsRejected() {
        Agent a = FakeAgent.of("a", AuthorityLevel.OBSERVE, Set.of(DecisionAction.ALLOW), DecisionAction.ALLOW, 0.9);
        assertThrows(UnscopedInvocationException.class,
                () -> harness.invoke(a, new AgentInput("", "u", Map.of(), Map.of())));
        assertThrows(UnscopedInvocationException.class,
                () -> harness.invoke(a, new AgentInput("t", "", Map.of(), Map.of())));
    }

    // §9 — Gate centralized: the agent cannot self-approve (§4, INV-1) -------------------------
    @Test
    void agentCannotSetAutoEnforced() {
        Agent a = new FakeAgent("a", AuthorityLevel.BLOCK, Set.of(DecisionAction.BLOCK),
                (in, tools) -> new Decision(DecisionAction.BLOCK, 0.5, "block", true)); // tries to self-approve
        AgentOutput out = harness.invoke(a, REQ);
        assertFalse(out.decision().autoEnforced()); // harness overrode the agent's flag
    }

    @Test
    void highConfidenceWithinAuthorityAutoEnforces() {
        Agent a = FakeAgent.of("a", AuthorityLevel.BLOCK, Set.of(DecisionAction.BLOCK), DecisionAction.BLOCK, 0.96);
        assertTrue(harness.invoke(a, REQ).decision().autoEnforced());
    }

    // §9 — Gate non-disableable: threshold floor is 0.80 (G-3, G-4) ----------------------------
    @Test
    void thresholdNeverBelowBase() {
        ConfidenceGate gate = new ConfidenceGate();
        for (AuthorityLevel level : AuthorityLevel.values()) {
            assertTrue(gate.thresholdFor(level) >= 0.80);
        }
    }

    // §9 — Low-confidence routing = 100% (§4 G-2) ---------------------------------------------
    @Test
    void lowConfidenceAlwaysRoutesToHuman() {
        for (double c : new double[]{0.0, 0.3, 0.5, 0.79}) {
            setUp();
            Agent a = FakeAgent.of("a", AuthorityLevel.ALERT, Set.of(DecisionAction.ALERT), DecisionAction.ALERT, c);
            AgentOutput out = harness.invoke(a, REQ);
            assertFalse(out.decision().autoEnforced());
            assertEquals(1, review.items().size());
            assertEquals("low_confidence", review.items().get(0).reason());
        }
    }

    // §9 — Gate bypass counter stays 0 (§4.2) -------------------------------------------------
    @Test
    void bypassCounterIsZero() {
        for (double c : new double[]{0.0, 0.5, 0.8, 0.96, 1.0}) {
            Agent a = FakeAgent.of("a", AuthorityLevel.BLOCK, Set.of(DecisionAction.BLOCK), DecisionAction.BLOCK, c);
            harness.invoke(a, REQ);
        }
        assertEquals(0, obs.counter(Harness.BYPASS_COUNTER));
    }

    // §9 — Tools default-deny; out-of-allowlist refused + security event (§5, INV-2) ----------
    @Test
    void unauthorizedToolIsRefusedAndLogged() {
        Agent a = new FakeAgent("a", AuthorityLevel.ALERT,
                Set.of(DecisionAction.ALERT, DecisionAction.DEFER),
                (in, tools) -> {
                    tools.call("db", Map.of()); // not granted → throws inside decide
                    return Decision.propose(DecisionAction.ALERT, 0.9, "unreached");
                });
        AgentOutput out = harness.invoke(a, REQ);
        assertEquals(DecisionAction.DEFER, out.decision().action()); // safe failure default
        assertTrue(audit.securityEvents().stream().anyMatch(e -> e.kind().equals("tool_not_authorized")));
    }

    @Test
    void authorizedToolCallSucceeds() {
        registry.registerTool("db", args -> "row");
        registry.grant("a", Set.of("db"));
        Agent a = new FakeAgent("a", AuthorityLevel.BLOCK, Set.of(DecisionAction.ALLOW),
                (in, tools) -> {
                    Object r = tools.call("db", Map.of("q", 1));
                    return Decision.propose(DecisionAction.ALLOW, 0.95, "ok:" + r);
                });
        AgentOutput out = harness.invoke(a, REQ);
        assertEquals(DecisionAction.ALLOW, out.decision().action());
        assertTrue(audit.securityEvents().isEmpty());
    }

    // §9 — No wildcards (§5 T-3) --------------------------------------------------------------
    @Test
    void wildcardAllowlistRejected() {
        assertThrows(ToolRegistrationException.class, () -> registry.grant("a", Set.of("*")));
    }

    @Test
    void wildcardToolNameRejected() {
        assertThrows(ToolRegistrationException.class, () -> registry.registerTool("db*", args -> null));
    }

    // §9 — Supervisor holds no tools (§6.3 T-4) ----------------------------------------------
    @Test
    void supervisorWithToolsRejected() {
        registry.grant("sup", Set.of("db"));
        Agent sup = FakeAgent.of("sup", AuthorityLevel.BLOCK, Set.of(DecisionAction.ALLOW), DecisionAction.ALLOW, 0.9);
        Agent w = FakeAgent.of("w", AuthorityLevel.ALERT, Set.of(DecisionAction.ALERT), DecisionAction.ALERT, 0.9);
        assertThrows(ToolRegistrationException.class, () -> new SupervisorWorkers(harness, sup, List.of(w)));
    }

    @Test
    void supervisorWorkersReconcilesToSafest() {
        Agent sup = FakeAgent.of("sup", AuthorityLevel.BLOCK, Set.of(DecisionAction.ALLOW), DecisionAction.ALLOW, 0.9);
        Agent wAllow = FakeAgent.of("w1", AuthorityLevel.OBSERVE, Set.of(DecisionAction.ALLOW), DecisionAction.ALLOW, 0.9);
        Agent wBlock = FakeAgent.of("w2", AuthorityLevel.BLOCK, Set.of(DecisionAction.BLOCK), DecisionAction.BLOCK, 0.97);
        var result = new SupervisorWorkers(harness, sup, List.of(wAllow, wBlock)).run(REQ);
        assertEquals(DecisionAction.BLOCK, result.reconciledAction()); // BLOCK wins the hierarchy
        assertEquals(Set.of("w1", "w2"), result.workerOutputs().keySet());
    }

    // §9 — No self-escalation: over-authority action is refused (§3.3) ------------------------
    @Test
    void agentCannotEscalateAuthority() {
        Agent a = FakeAgent.of("a", AuthorityLevel.OBSERVE, Set.of(DecisionAction.BLOCK), DecisionAction.BLOCK, 0.99);
        AgentOutput out = harness.invoke(a, REQ);
        assertEquals(DecisionAction.DEFER, out.decision().action()); // downgraded to safe default
        assertTrue(audit.securityEvents().stream().anyMatch(e -> e.kind().equals("authority_violation")));
    }

    // §9 — Audit append-only + PII-redacted; BLOCK/ALERT carry explanations (§7.3, INV-4) -----
    @Test
    void auditRedactsPii() {
        Agent a = new FakeAgent("a", AuthorityLevel.ALERT, Set.of(DecisionAction.ALERT),
                (in, tools) -> Decision.propose(DecisionAction.ALERT, 0.9, "contact bob@example.com now"));
        harness.invoke(a, REQ);
        String rationale = audit.entries().get(0).rationale();
        assertFalse(rationale.contains("bob@example.com"));
        assertTrue(rationale.contains("[REDACTED_EMAIL]"));
    }

    @Test
    void blockWithoutRationaleFallsBack() {
        Agent a = new FakeAgent("a", AuthorityLevel.BLOCK, Set.of(DecisionAction.BLOCK),
                (in, tools) -> Decision.propose(DecisionAction.BLOCK, 0.99, ""));
        AgentOutput out = harness.invoke(a, REQ);
        assertEquals(DecisionAction.DEFER, out.decision().action()); // unexplained BLOCK never enforces
        assertFalse(out.decision().autoEnforced());
    }

    // §9 — Kill switch (§7.6) -----------------------------------------------------------------
    @Test
    void killSwitchShortCircuitsAndRoutes() {
        Agent a = new FakeAgent("a", AuthorityLevel.BLOCK, Set.of(DecisionAction.BLOCK),
                (in, tools) -> {
                    throw new AssertionError("agent must NOT run while kill switch is engaged");
                });
        kill.engage();
        AgentOutput out = harness.invoke(a, REQ);
        assertEquals(DecisionAction.DEFER, out.decision().action());
        assertEquals("kill_switch", review.items().get(0).reason());
    }

    // §9 — Safe failure defaults: never fail open (§8) ----------------------------------------
    @Test
    void agentExceptionResolvesSafely() {
        Agent a = new FakeAgent("a", AuthorityLevel.BLOCK, Set.of(DecisionAction.BLOCK),
                (in, tools) -> {
                    throw new RuntimeException("llm exploded");
                });
        AgentOutput out = harness.invoke(a, REQ);
        assertFalse(out.decision().autoEnforced());
        assertTrue(out.decision().confidence() <= 0.6);
        assertFalse(review.items().isEmpty());
    }

    @Test
    void reconcilePrefersBlock() {
        assertEquals(DecisionAction.BLOCK,
                Decisions.reconcile(List.of(DecisionAction.ALLOW, DecisionAction.SUGGEST, DecisionAction.BLOCK)));
        assertEquals(DecisionAction.DEFER,
                Decisions.reconcile(List.of(DecisionAction.ALLOW, DecisionAction.DEFER)));
    }
}
