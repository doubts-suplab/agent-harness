package com.agentharness.adapters;

import com.agentharness.ports.PolicyPort;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Immutable rule-based {@link PolicyPort} (harness-protocol.md §7). Rules are fixed at construction, so
 * a policy cannot be mutated at runtime — upholding no-self-escalation (INV-3). The first matching rule
 * wins; otherwise {@code defaultAllow} decides.
 */
public final class RuleBasedPolicy implements PolicyPort {

    /** A single allow/deny rule. {@code null} in a field means 'any'. */
    public record PolicyRule(boolean allow, String agent, String action, String tenant) {

        public boolean matches(String agentName, String actionName, String tenantId) {
            return (agent == null || agent.equals(agentName))
                    && (action == null || action.equals(actionName))
                    && (tenant == null || tenant.equals(tenantId));
        }
    }

    private final List<PolicyRule> rules;
    private final boolean defaultAllow;

    public RuleBasedPolicy(List<PolicyRule> rules, boolean defaultAllow) {
        this.rules = List.copyOf(rules); // defensive, immutable
        this.defaultAllow = defaultAllow;
    }

    @Override
    public boolean permits(String agentName, String action, String tenantId) {
        for (PolicyRule rule : rules) {
            if (rule.matches(agentName, action, tenantId)) {
                return rule.allow();
            }
        }
        return defaultAllow;
    }

    /**
     * Load an immutable policy from a durable text file. Format: a first optional line
     * {@code default allow|deny}; then one rule per line {@code allow|deny agent action tenant}, where
     * {@code *} means 'any'. Blank lines and {@code #} comments are ignored.
     */
    public static RuleBasedPolicy load(Path path) {
        boolean defaultAllow = true;
        List<PolicyRule> rules = new ArrayList<>();
        List<String> lines;
        try {
            lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("cannot read policy file", e);
        }
        for (String raw : lines) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            String[] parts = line.split("\\s+");
            if (parts[0].equals("default") && parts.length == 2) {
                defaultAllow = parts[1].equalsIgnoreCase("allow");
                continue;
            }
            boolean allow = parts[0].equalsIgnoreCase("allow");
            rules.add(new PolicyRule(allow, any(parts, 1), any(parts, 2), any(parts, 3)));
        }
        return new RuleBasedPolicy(rules, defaultAllow);
    }

    private static String any(String[] parts, int i) {
        if (i >= parts.length || parts[i].equals("*")) {
            return null;
        }
        return parts[i];
    }
}
