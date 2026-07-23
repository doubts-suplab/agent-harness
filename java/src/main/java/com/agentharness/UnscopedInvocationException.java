package com.agentharness;

/** AgentInput is missing tenant/user scope (harness-protocol.md §2.1). */
public class UnscopedInvocationException extends HarnessException {
    public UnscopedInvocationException(String message) {
        super(message);
    }
}
