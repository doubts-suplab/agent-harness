package com.agentharness.interop;

import com.agentharness.Agent;
import com.agentharness.Harness;
import com.agentharness.adapters.InMemoryHumanReview;
import com.agentharness.model.AgentInput;
import com.agentharness.model.AgentOutput;
import com.agentharness.model.AuthorityLevel;
import com.agentharness.model.DecisionAction;
import com.agentharness.ConfidenceGate;
import com.agentharness.ToolRegistry;
import com.agentharness.adapters.InMemoryAudit;
import com.agentharness.adapters.InMemoryKillSwitch;
import com.agentharness.adapters.InMemoryObservability;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Demonstrates the aether-grid migration: a legacy governance agent that used to compute
 * {@code autoEnforced} itself now delegates that to the harness's single confidence gate. These mirror
 * grid's {@code GovernanceAgentTest} threshold cases — but the 0.8/0.95 logic lives in ONE place.
 */
class LegacyAgentAdapterTest {

    private static final AgentInput REQ = new AgentInput("t", "u", Map.of(), Map.of());

    private Harness harness() {
        return new Harness(new ToolRegistry(), new InMemoryAudit(), new InMemoryHumanReview(),
                new InMemoryObservability(), new InMemoryKillSwitch(), new ConfidenceGate());
    }

    /** A legacy grid-style governance agent: emits BLOCK/ALLOW with a confidence, nothing more. */
    private Agent governance(DecisionAction action, double confidence) {
        LegacyAgentAdapter.LegacyAgent legacy =
                input -> new LegacyAgentAdapter.LegacyResult(action, confidence, "policy check");
        return new LegacyAgentAdapter("governance-agent", AuthorityLevel.BLOCK,
                Set.of(DecisionAction.ALLOW, DecisionAction.BLOCK, DecisionAction.ALERT, DecisionAction.DEFER),
                legacy);
    }

    @Test
    void blockAboveThresholdAutoEnforces() {
        AgentOutput out = harness().invoke(governance(DecisionAction.BLOCK, 0.96), REQ);
        assertEquals(DecisionAction.BLOCK, out.decision().action());
        assertTrue(out.decision().autoEnforced());
    }

    @Test
    void blockBelowThresholdRoutesToHuman() {
        InMemoryHumanReview review = new InMemoryHumanReview();
        Harness h = new Harness(new ToolRegistry(), new InMemoryAudit(), review,
                new InMemoryObservability(), new InMemoryKillSwitch(), new ConfidenceGate());
        AgentOutput out = h.invoke(governance(DecisionAction.BLOCK, 0.65), REQ);
        assertEquals(DecisionAction.BLOCK, out.decision().action());
        assertFalse(out.decision().autoEnforced()); // gate, not the agent, decided this
        assertEquals(1, review.items().size());
    }
}
