package com.agentharness;

import com.agentharness.model.AuthorityLevel;

import java.util.Set;

/**
 * Side-effect gating policy (harness-protocol.md §5 T-5, §5.3, ADR-0011).
 *
 * <p>Every registered tool declares a side-effect class: {@code none | read | write | external}. Before
 * a tool executes, the harness consults this policy. {@code none}/{@code read} calls are ungated.
 * {@code write}/{@code external} calls are gated: they MUST clear a confidence threshold and MUST NOT be
 * issued by a read-only ({@code OBSERVE}-authority) agent. A gated call that fails is refused before
 * execution and recorded as a security event.
 *
 * @param writeThreshold    minimum confidence for a {@code write} call
 * @param externalThreshold minimum confidence for an {@code external} call
 */
public record SideEffectPolicy(double writeThreshold, double externalThreshold) {

    /** The side-effect classes subject to gating (spec §5.3). */
    public static final Set<String> GATED_CLASSES = Set.of("write", "external");

    /** Reference defaults: write ≥ 0.85, external ≥ 0.95. */
    public static SideEffectPolicy defaults() {
        return new SideEffectPolicy(0.85, 0.95);
    }

    public static boolean isGated(String sideEffect) {
        return sideEffect != null && GATED_CLASSES.contains(sideEffect);
    }

    public double thresholdFor(String sideEffect) {
        return switch (sideEffect == null ? "" : sideEffect) {
            case "write" -> writeThreshold;
            case "external" -> externalThreshold;
            default -> 0.0;
        };
    }

    /**
     * True if a call with this side-effect class may execute (spec §5.3). Ungated classes always pass;
     * for gated classes a read-only ({@code OBSERVE}) agent is never permitted, and {@code confidence}
     * (null → 0.0) MUST meet the class threshold.
     */
    public boolean permits(String sideEffect, Double confidence, AuthorityLevel authority) {
        if (!isGated(sideEffect)) {
            return true;
        }
        if (authority == AuthorityLevel.OBSERVE) {
            return false;
        }
        double c = confidence == null ? 0.0 : confidence;
        return c >= thresholdFor(sideEffect);
    }
}
