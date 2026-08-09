package com.suplab.agentharness;

import com.suplab.agentharness.model.AuthorityLevel;
import com.suplab.agentharness.model.Decision;
import com.suplab.agentharness.model.DecisionAction;

import java.util.EnumSet;
import java.util.Map;

/**
 * The confidence gate (harness-protocol.md §4, ADR-0003). Centralized, runs on every invocation, and
 * cannot be disabled — there is no "off" state. It is the only place {@code autoEnforced} is set. This
 * replaces grid's duplicated per-agent {@code confidence >= 0.8} checks with one testable component.
 */
public final class ConfidenceGate {

    /** G-3: the floor for any externally-effecting action. The gate never enforces below this. */
    public static final double BASE_THRESHOLD = 0.80;

    private static final Map<AuthorityLevel, Double> THRESHOLDS = Map.of(
            AuthorityLevel.ALERT, 0.80,
            AuthorityLevel.RATE_LIMIT, 0.85,
            AuthorityLevel.BLOCK, 0.95
    );

    private static final EnumSet<DecisionAction> ALWAYS_REVIEW =
            EnumSet.of(DecisionAction.DEFER, DecisionAction.SUGGEST);

    /** Effective auto-enforce threshold for an authority level (never below BASE_THRESHOLD). */
    public double thresholdFor(AuthorityLevel authority) {
        return Math.max(BASE_THRESHOLD, THRESHOLDS.getOrDefault(authority, BASE_THRESHOLD));
    }

    /** Return a gated copy of {@code decision} with {@code autoEnforced} decided by the gate. */
    public Decision evaluate(Decision decision, AuthorityLevel authority) {
        return decision.withAutoEnforced(shouldAutoEnforce(decision, authority));
    }

    private boolean shouldAutoEnforce(Decision decision, AuthorityLevel authority) {
        // G-5: OBSERVE/SUGGEST-authority agents never auto-enforce, regardless of confidence.
        if (!authority.atLeast(AuthorityLevel.ALERT)) {
            return false;
        }
        // DEFER/SUGGEST outcomes always route to a human (spec §3.3).
        if (ALWAYS_REVIEW.contains(decision.action())) {
            return false;
        }
        return decision.confidence() >= thresholdFor(authority);
    }

    /**
     * A bypass is an auto-enforced decision that should not have cleared the gate. In a correct system
     * this is always false (spec §4.2). Used defensively by the harness to feed the bypass counter.
     */
    public boolean isBypass(Decision decision, AuthorityLevel authority) {
        return decision.autoEnforced() && !shouldAutoEnforce(decision, authority);
    }
}
