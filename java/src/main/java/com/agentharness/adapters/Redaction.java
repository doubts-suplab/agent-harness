package com.agentharness.adapters;

import java.util.List;
import java.util.regex.Pattern;

/** PII/secret redaction for audit writes (harness-protocol.md §7.3). Zero PII in logs is a P1 condition. */
public final class Redaction {

    private record Rule(Pattern pattern, String replacement) {
    }

    // Order matters (JWT/card before generic digits).
    private static final List<Rule> RULES = List.of(
            new Rule(Pattern.compile("[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+"), "[REDACTED_JWT]"),
            new Rule(Pattern.compile("\\b[\\w.%+-]+@[\\w.-]+\\.[A-Za-z]{2,}\\b"), "[REDACTED_EMAIL]"),
            new Rule(Pattern.compile("\\b(?:\\d[ -]*?){13,16}\\b"), "[REDACTED_CARD]"),
            new Rule(Pattern.compile("\\b\\d{3}-\\d{2}-\\d{4}\\b"), "[REDACTED_SSN]"),
            new Rule(Pattern.compile("\\b(?:\\+?\\d[\\d -]{8,}\\d)\\b"), "[REDACTED_PHONE]"),
            new Rule(Pattern.compile("\\b(?:sk|pk|ghp|xox[baprs])[-_][A-Za-z0-9]{8,}\\b"), "[REDACTED_KEY]")
    );

    private Redaction() {
    }

    public static String redact(String text) {
        if (text == null) {
            return "";
        }
        String out = text;
        for (Rule rule : RULES) {
            out = rule.pattern().matcher(out).replaceAll(rule.replacement());
        }
        return out;
    }
}
