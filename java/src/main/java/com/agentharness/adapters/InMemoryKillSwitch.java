package com.agentharness.adapters;

import com.agentharness.ports.KillSwitchPort;

/** In-memory kill switch (harness-protocol.md §7.6). */
public final class InMemoryKillSwitch implements KillSwitchPort {

    private volatile boolean engaged;

    public InMemoryKillSwitch() {
        this(false);
    }

    public InMemoryKillSwitch(boolean engaged) {
        this.engaged = engaged;
    }

    @Override
    public boolean isEngaged() {
        return engaged;
    }

    public void engage() {
        this.engaged = true;
    }

    public void disengage() {
        this.engaged = false;
    }
}
