package com.agentharness.model;

/**
 * An agent's static capability ceiling (harness-protocol.md §3.1). Ordered: higher = more authority.
 * MUST NOT change at runtime (no self-escalation, INV-3).
 */
public enum AuthorityLevel {
    OBSERVE,
    SUGGEST,
    ALERT,
    RATE_LIMIT,
    BLOCK;

    /** True if this level is at least as high as {@code other}. */
    public boolean atLeast(AuthorityLevel other) {
        return this.ordinal() >= other.ordinal();
    }
}
