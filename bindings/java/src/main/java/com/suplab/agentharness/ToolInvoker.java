package com.suplab.agentharness;

import java.util.Map;

/**
 * Scoped tool access handed to an agent for one invocation (harness-protocol.md §5). {@code call}
 * authorizes against the agent's registry allowlist before any side effect; an unauthorized name throws
 * {@link ToolNotAuthorizedException} and is recorded as a security event.
 *
 * <p>For a gated ({@code write}/{@code external}) tool, use the {@code confidence} overload — the
 * harness's side-effect policy (spec §5.3) refuses the call before execution unless it clears the class
 * threshold. Read-only ({@code none}/{@code read}) tools ignore confidence.
 */
public interface ToolInvoker {

    /** Call a tool with no declared confidence (intended for read-only tools). */
    Object call(String toolName, Map<String, Object> arguments);

    /** Call a gated tool, supplying the confidence the side-effect policy checks (spec §5.3). */
    Object call(String toolName, Map<String, Object> arguments, double confidence);
}
