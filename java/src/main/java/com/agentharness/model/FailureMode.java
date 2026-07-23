package com.agentharness.model;

/**
 * Failure-mode safe defaults (harness-protocol.md §8). Every failure resolves to a non-enforcing
 * decision with lowered confidence — an agent never fails open.
 */
public enum FailureMode {
    LLM_UNAVAILABLE(DecisionAction.ALLOW, 0.5),
    MEMORY_TIMEOUT(DecisionAction.DEFER, 0.6),
    MISSING_CONTEXT(DecisionAction.DEFER, 0.5),
    TOOL_FAILURE(DecisionAction.DEFER, 0.6),
    BAD_OUTPUT(DecisionAction.DEFER, 0.0),
    OUT_OF_AUTHORITY(DecisionAction.DEFER, 0.0);

    private final DecisionAction action;
    private final double confidence;

    FailureMode(DecisionAction action, double confidence) {
        this.action = action;
        this.confidence = confidence;
    }

    /** The safe fallback decision for this failure mode (auto_enforced stays false; spec §8). */
    public Decision toDecision(String detail) {
        String rationale = "harness failure default (" + name().toLowerCase() + ")";
        if (detail != null && !detail.isBlank()) {
            rationale = rationale + ": " + detail;
        }
        return new Decision(action, confidence, rationale, false);
    }
}
