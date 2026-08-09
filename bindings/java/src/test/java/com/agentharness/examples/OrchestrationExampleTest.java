package com.agentharness.examples;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

/** Smoke test: the orchestration example runs end-to-end and keeps the gate bypass counter at 0. */
class OrchestrationExampleTest {

    @Test
    void exampleRunsAndReportsZeroBypasses() {
        String summary = OrchestrationExample.run();
        assertTrue(summary.contains("Pipeline"));
        assertTrue(summary.contains("Fan-out"));
        assertTrue(summary.contains("Debate"));
        assertTrue(summary.contains("Supervisor"));
        assertTrue(summary.contains("confidence_gate_bypass_total = 0"));
    }
}
