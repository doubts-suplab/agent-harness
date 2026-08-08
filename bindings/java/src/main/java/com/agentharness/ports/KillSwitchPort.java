package com.agentharness.ports;

/** System-wide stop without a code deploy (harness-protocol.md §7.6). When engaged, nothing auto-enforces. */
public interface KillSwitchPort {
    boolean isEngaged();
}
