package com.suplab.agentharness.ports;

import java.util.Optional;

/** Scoped agent-visible memory (harness-protocol.md §7). Every call is scoped by tenant. */
public interface MemoryPort {

    Optional<Object> read(String tenantId, String userId, String key);

    void write(String tenantId, String userId, String key, Object value);
}
