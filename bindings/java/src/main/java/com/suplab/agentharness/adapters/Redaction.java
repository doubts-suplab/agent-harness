package com.suplab.agentharness.adapters;

/**
 * PII/secret redaction for audit writes (harness-protocol.md §7.3). Zero PII in logs is a P1 condition.
 * Thin facade over the default {@link RedactionStrategy}; use a {@code RedactionStrategy} directly for a
 * customized rule set.
 */
public final class Redaction {

    private Redaction() {
    }

    public static String redact(String text) {
        return RedactionStrategy.DEFAULT.redact(text);
    }
}
