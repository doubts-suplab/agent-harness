package com.agentharness;

import java.util.Map;

/**
 * Scoped tool access handed to an agent for one invocation (harness-protocol.md §5). {@code call}
 * authorizes against the agent's registry allowlist before any side effect; an unauthorized name throws
 * {@link ToolNotAuthorizedException} and is recorded as a security event.
 */
public interface ToolInvoker {
    Object call(String toolName, Map<String, Object> arguments);
}
