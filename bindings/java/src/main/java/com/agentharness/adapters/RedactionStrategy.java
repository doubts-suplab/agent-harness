package com.agentharness.adapters;

import java.util.ArrayList;
import java.util.List;
import java.util.function.UnaryOperator;
import java.util.regex.Pattern;

/**
 * Pluggable PII/secret redaction (harness-protocol.md §7.3).
 *
 * <p>Redaction runs before every audit write; zero PII in logs is a P1 condition. The default strategy
 * covers common patterns, but every deployment has its own sensitive shapes, so the strategy is
 * <b>pluggable</b>: extend it with {@link #withRule} or build one from scratch. It implements
 * {@link UnaryOperator}, so it drops directly into any port that takes a {@code redactor}.
 *
 * <p>The default patterns are best-effort, not a guarantee: order matters (specific before generic) and
 * no regex set is exhaustive. Treat redaction as defense-in-depth.
 */
public final class RedactionStrategy implements UnaryOperator<String> {

    public record Rule(Pattern pattern, String replacement) {
    }

    // spec §7.3 default rules. Order matters (JWT/card before generic digit runs).
    static final List<Rule> DEFAULT_RULES = List.of(
            new Rule(Pattern.compile("[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+"), "[REDACTED_JWT]"),
            new Rule(Pattern.compile("\\b[\\w.%+-]+@[\\w.-]+\\.[A-Za-z]{2,}\\b"), "[REDACTED_EMAIL]"),
            new Rule(Pattern.compile("\\b(?:\\d[ -]*?){13,16}\\b"), "[REDACTED_CARD]"),
            new Rule(Pattern.compile("\\b\\d{3}-\\d{2}-\\d{4}\\b"), "[REDACTED_SSN]"),
            new Rule(Pattern.compile("\\b(?:\\+?\\d[\\d -]{8,}\\d)\\b"), "[REDACTED_PHONE]"),
            new Rule(Pattern.compile("\\b(?:sk|pk|ghp|xox[baprs])[-_][A-Za-z0-9]{8,}\\b"), "[REDACTED_KEY]"));

    public static final RedactionStrategy DEFAULT = new RedactionStrategy(DEFAULT_RULES);

    private final List<Rule> rules;

    public RedactionStrategy(List<Rule> rules) {
        this.rules = List.copyOf(rules); // immutable
    }

    public static RedactionStrategy defaults() {
        return DEFAULT;
    }

    public String redact(String text) {
        if (text == null) {
            return "";
        }
        String out = text;
        for (Rule rule : rules) {
            out = rule.pattern().matcher(out).replaceAll(rule.replacement());
        }
        return out;
    }

    @Override
    public String apply(String text) {
        return redact(text);
    }

    /** Return a new strategy with one extra rule appended (the base stays immutable). */
    public RedactionStrategy withRule(String pattern, String replacement) {
        List<Rule> extended = new ArrayList<>(rules);
        extended.add(new Rule(Pattern.compile(pattern), replacement));
        return new RedactionStrategy(extended);
    }
}
