package com.agentharness.model;

import java.util.List;
import java.util.Map;

/** The two-axis binding rule and the Decision Hierarchy (harness-protocol.md §3.3). */
public final class Decisions {

    private Decisions() {
    }

    // §3.3: the minimum authority a DecisionAction requires.
    private static final Map<DecisionAction, AuthorityLevel> MIN_AUTHORITY = Map.of(
            DecisionAction.ALLOW, AuthorityLevel.OBSERVE,   // no external effect
            DecisionAction.DEFER, AuthorityLevel.OBSERVE,   // routes to a human; no autonomous effect
            DecisionAction.SUGGEST, AuthorityLevel.SUGGEST,
            DecisionAction.ALERT, AuthorityLevel.ALERT,
            DecisionAction.BLOCK, AuthorityLevel.BLOCK
    );

    // §3.3 Decision Hierarchy over the action set: BLOCK > ALERT > SUGGEST > DEFER > ALLOW.
    private static final Map<DecisionAction, Integer> PRECEDENCE = Map.of(
            DecisionAction.BLOCK, 5,
            DecisionAction.ALERT, 3,
            DecisionAction.SUGGEST, 2,
            DecisionAction.DEFER, 1,
            DecisionAction.ALLOW, 0
    );

    public static AuthorityLevel minAuthorityFor(DecisionAction action) {
        return MIN_AUTHORITY.get(action);
    }

    /** True if an agent at {@code authority} may emit {@code action} (spec §3.3). */
    public static boolean actionWithinAuthority(DecisionAction action, AuthorityLevel authority) {
        return authority.atLeast(MIN_AUTHORITY.get(action));
    }

    /** Reconcile competing decisions toward the safer action (spec §3.3, §6.2). */
    public static DecisionAction reconcile(List<DecisionAction> actions) {
        if (actions == null || actions.isEmpty()) {
            throw new IllegalArgumentException("cannot reconcile an empty list of actions");
        }
        return actions.stream().max((a, b) -> PRECEDENCE.get(a) - PRECEDENCE.get(b)).orElseThrow();
    }
}
