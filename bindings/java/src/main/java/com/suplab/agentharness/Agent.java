package com.suplab.agentharness;

import com.suplab.agentharness.model.AgentInput;
import com.suplab.agentharness.model.AuthorityLevel;
import com.suplab.agentharness.model.Decision;
import com.suplab.agentharness.model.DecisionAction;

import java.util.Set;

/**
 * A decision-making agent (harness-protocol.md §10). Mirrors grid's {@code Agent} SPI but the harness
 * (not the agent) owns the confidence gate, tool registry, and authority enforcement around {@link #decide}.
 * An agent proposes a Decision via {@link Decision#propose}; it never sets {@code autoEnforced}.
 */
public interface Agent {

    String name();

    AuthorityLevel authorityLevel();

    Set<DecisionAction> capabilities();

    Decision decide(AgentInput input, ToolInvoker tools);
}
