package com.suplab.agentharness;

/**
 * An agent attempted a tool not in its allowlist (harness-protocol.md §5, INV-2). Raised before any
 * side effect; recorded as a security event by the harness.
 */
public class ToolNotAuthorizedException extends HarnessException {

    private final String agentName;
    private final String toolName;

    public ToolNotAuthorizedException(String agentName, String toolName) {
        super("agent '" + agentName + "' is not authorized to call tool '" + toolName + "'");
        this.agentName = agentName;
        this.toolName = toolName;
    }

    public String agentName() {
        return agentName;
    }

    public String toolName() {
        return toolName;
    }
}
