package com.agentharness.model;

/**
 * The outcome an agent proposes (harness-protocol.md §2.2, §4).
 *
 * <p>{@code autoEnforced} is owned by the harness, not the agent. Agents build a decision with
 * {@link #propose}; the confidence gate returns a gated copy via {@link #withAutoEnforced}.
 * The record is immutable, so an agent cannot mutate the flag after the gate has set it.
 */
public record Decision(DecisionAction action, double confidence, String rationale, boolean autoEnforced) {

    public Decision {
        if (action == null) {
            throw new IllegalArgumentException("action is required");
        }
        rationale = rationale == null ? "" : rationale;
    }

    /** An agent's proposal. {@code autoEnforced} is always false here — only the gate may set it. */
    public static Decision propose(DecisionAction action, double confidence, String rationale) {
        return new Decision(action, confidence, rationale, false);
    }

    public Decision withAutoEnforced(boolean value) {
        return new Decision(action, confidence, rationale, value);
    }

    /** Protocol-level validation of the decision shape (spec §2.2). */
    public void validate() {
        if (confidence < 0.0 || confidence > 1.0) {
            throw new IllegalArgumentException("confidence " + confidence + " out of range [0.0, 1.0]");
        }
        if ((action == DecisionAction.BLOCK || action == DecisionAction.ALERT)
                && rationale.isBlank()) {
            throw new IllegalArgumentException(action + " decisions MUST carry a human-readable rationale");
        }
    }
}
