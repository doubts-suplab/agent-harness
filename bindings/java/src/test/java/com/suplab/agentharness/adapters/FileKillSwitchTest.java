package com.suplab.agentharness.adapters;

import com.suplab.agentharness.Agent;
import com.suplab.agentharness.ConfidenceGate;
import com.suplab.agentharness.Harness;
import com.suplab.agentharness.ToolInvoker;
import com.suplab.agentharness.ToolRegistry;
import com.suplab.agentharness.model.AgentInput;
import com.suplab.agentharness.model.AgentOutput;
import com.suplab.agentharness.model.AuthorityLevel;
import com.suplab.agentharness.model.Decision;
import com.suplab.agentharness.model.DecisionAction;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Cross-process kill-switch (file signal) tests (harness-protocol.md §7.6). */
class FileKillSwitchTest {

    @Test
    void startsDisengaged(@TempDir Path dir) {
        assertFalse(new FileKillSwitch(dir.resolve("kill")).isEngaged());
    }

    @Test
    void engageAndDisengageAreIdempotent(@TempDir Path dir) {
        FileKillSwitch ks = new FileKillSwitch(dir.resolve("nested/kill"));
        ks.engage();
        ks.engage();
        assertTrue(ks.isEngaged());
        ks.disengage();
        ks.disengage();
        assertFalse(ks.isEngaged());
    }

    @Test
    void tripPropagatesAcrossInstances(@TempDir Path dir) {
        Path path = dir.resolve("kill");
        FileKillSwitch procA = new FileKillSwitch(path);
        FileKillSwitch procB = new FileKillSwitch(path);
        procA.engage();
        assertTrue(procB.isEngaged()); // the other "process" sees the trip
        procB.disengage();
        assertFalse(procA.isEngaged());
    }

    @Test
    void engagedSwitchRoutesEverythingToHumanReview(@TempDir Path dir) {
        FileKillSwitch kill = new FileKillSwitch(dir.resolve("kill"));
        kill.engage();
        InMemoryHumanReview review = new InMemoryHumanReview();
        Harness harness = new Harness(new ToolRegistry(), new InMemoryAudit(), review,
                new InMemoryObservability(), kill, new ConfidenceGate());
        Agent agent = new StubAgent("a", AuthorityLevel.BLOCK, Set.of(DecisionAction.BLOCK),
                (in, tools) -> Decision.propose(DecisionAction.BLOCK, 0.99, "block"));
        AgentOutput out = harness.invoke(agent, new AgentInput("t1", "u1", Map.of(), Map.of()));
        assertEquals(DecisionAction.DEFER, out.decision().action()); // short-circuited by the kill switch
        assertFalse(out.decision().autoEnforced());
    }

    private record StubAgent(String name, AuthorityLevel authorityLevel, Set<DecisionAction> capabilities,
                             java.util.function.BiFunction<AgentInput, ToolInvoker, Decision> decide)
            implements Agent {
        @Override
        public Decision decide(AgentInput input, ToolInvoker tools) {
            return decide.apply(input, tools);
        }
    }
}
