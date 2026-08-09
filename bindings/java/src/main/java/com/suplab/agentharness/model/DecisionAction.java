package com.suplab.agentharness.model;

/** The dynamic outcome of a single invocation (harness-protocol.md §3.2). */
public enum DecisionAction {
    ALLOW,
    BLOCK,
    ALERT,
    SUGGEST,
    DEFER
}
