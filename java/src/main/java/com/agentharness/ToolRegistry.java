package com.agentharness;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;

/**
 * The tool registry — the governance boundary for agent capabilities (harness-protocol.md §5, ADR-0004).
 * Default-deny: a tool not in an agent's allowlist is unreachable. No wildcards. Holds the concrete tool
 * implementations. (Net-new for grid, which has no tool concept today.)
 */
public final class ToolRegistry {

    private static final Set<String> SIDE_EFFECTS = Set.of("none", "read", "write", "external");

    /** A registered tool. {@code impl} maps arguments to a result. */
    public record RegisteredTool(String name, String description, String sideEffect,
                                 Function<Map<String, Object>, Object> impl) {
    }

    private final Map<String, RegisteredTool> tools = new ConcurrentHashMap<>();
    private final Map<String, Set<String>> allowlists = new ConcurrentHashMap<>();

    public void registerTool(String name, String sideEffect, Function<Map<String, Object>, Object> impl) {
        if (name.contains("*")) {
            throw new ToolRegistrationException("tool name '" + name + "' must not contain a wildcard");
        }
        if (!SIDE_EFFECTS.contains(sideEffect)) {
            throw new ToolRegistrationException("unknown sideEffect '" + sideEffect + "'");
        }
        tools.put(name, new RegisteredTool(name, "", sideEffect, impl));
    }

    public void registerTool(String name, Function<Map<String, Object>, Object> impl) {
        registerTool(name, "read", impl);
    }

    /** Set an agent's explicit tool allowlist (spec §5 T-1, T-3). Wildcards are rejected. */
    public void grant(String agentName, Set<String> toolNames) {
        for (String n : toolNames) {
            if (n.contains("*")) {
                throw new ToolRegistrationException("wildcard permission '" + n + "' is forbidden (spec §5 T-3)");
            }
        }
        allowlists.put(agentName, Set.copyOf(toolNames));
    }

    public boolean isAuthorized(String agentName, String toolName) {
        return allowlists.getOrDefault(agentName, Set.of()).contains(toolName);
    }

    public Set<String> allowlist(String agentName) {
        return allowlists.getOrDefault(agentName, Set.of());
    }

    /** The declared side-effect class of a tool (spec §5 T-5), or {@code null} if unregistered. */
    public String sideEffect(String toolName) {
        RegisteredTool tool = tools.get(toolName);
        return tool == null ? null : tool.sideEffect();
    }

    /** Authorize (default-deny) then invoke. Unauthorized → ToolNotAuthorizedException (spec §5 T-1/T-2). */
    public Object invoke(String agentName, String toolName, Map<String, Object> arguments) {
        if (!isAuthorized(agentName, toolName)) {
            throw new ToolNotAuthorizedException(agentName, toolName);
        }
        RegisteredTool tool = tools.get(toolName);
        if (tool == null) {
            throw new ToolNotAuthorizedException(agentName, toolName);
        }
        return tool.impl().apply(arguments);
    }
}
