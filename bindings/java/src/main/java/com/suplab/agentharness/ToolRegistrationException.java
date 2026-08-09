package com.suplab.agentharness;

/** Invalid tool-registry configuration, e.g. a wildcard allowlist (harness-protocol.md §5 T-3). */
public class ToolRegistrationException extends HarnessException {
    public ToolRegistrationException(String message) {
        super(message);
    }
}
