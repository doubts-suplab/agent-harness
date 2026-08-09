package com.suplab.agentharness;

/**
 * A gated (write/external) tool call failed the side-effect policy (harness-protocol.md §5.3, T-5).
 * Thrown before any side effect; recorded as a security event by the harness.
 */
public final class SideEffectDeniedException extends HarnessException {

    private final transient String agentName;
    private final transient String toolName;
    private final transient String sideEffect;

    public SideEffectDeniedException(String agentName, String toolName, String sideEffect) {
        super("agent '" + agentName + "' may not call '" + sideEffect + "' tool '" + toolName
                + "' (side-effect policy, spec §5.3)");
        this.agentName = agentName;
        this.toolName = toolName;
        this.sideEffect = sideEffect;
    }

    public String agentName() {
        return agentName;
    }

    public String toolName() {
        return toolName;
    }

    public String sideEffect() {
        return sideEffect;
    }
}
