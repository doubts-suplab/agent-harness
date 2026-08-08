package com.agentharness.ports;

/**
 * Evaluate an agent action against immutable rules (harness-protocol.md §7). Rules are immutable at
 * runtime — an agent cannot loosen the rules that bind it (no self-escalation, INV-3).
 */
public interface PolicyPort {

    boolean permits(String agentName, String action, String tenantId);
}
